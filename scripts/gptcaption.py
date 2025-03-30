import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import datetime
from openai import OpenAI
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import time
import base64
from PIL import Image
import io
import json
from tqdm import tqdm
from string_utils import strings
from dotenv import load_dotenv, set_key

# Get the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from scripts directory
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# Global Settings
MAX_CONSECUTIVE_ERRORS = int(os.getenv('MAX_CONSECUTIVE_ERRORS', '5'))  # Default to 5, 0 or -1 to disable

# Token cost settings (GPT-4o mini)
TOKEN_COST_INPUT = 0.00000015   # $0.150 per 1M tokens
TOKEN_COST_OUTPUT = 0.00000060  # $0.600 per 1M tokens

# Global variables for error tracking
consecutive_errors = 0
failed_files = []

# Global variables for token tracking
total_prompt_tokens = 0
total_completion_tokens = 0
total_tokens = 0

# Global variables for progress tracking
total_images = 0
processed_images = 0
time_folder = None

# GUI variables (will be initialized later)
root = None
status_label = None
progress_var = None
generate_button = None
web_text_area = None
local_text_area = None
instructions_entry = None

# Variables for settings
batch_var = None
save_individual_var = None
save_local_var = None
overwrite_var = None
resolution_var = None
tier_var = None

# Progress tracking functions
def update_progress():
    """Update both GUI progress bar and status label."""
    global processed_images, total_images
    if total_images > 0:
        progress = (processed_images / total_images) * 100
        progress_var.set(progress)
        status_label.config(text=strings.get('ui.status.progress',
            current=processed_images,
            total=total_images,
            percent=progress
        ))
    root.update_idletasks()

def increment_progress():
    """Increment the progress counter and update display."""
    global processed_images
    processed_images += 1
    update_progress()

def update_status(message):
    status_label.config(text=message)
    root.update_idletasks()

class CreateToolTip(object):
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.tw = None

    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        # Create tooltip window
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        
        # Window management settings
        self.tw.wm_attributes("-topmost", True)  # Keep on top
        self.tw.wm_attributes("-toolwindow", True)  # Mark as tool window
        self.tw.wm_transient(self.widget)  # Set as transient window
        
        # Position the tooltip
        self.tw.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        label = ttk.Label(self.tw, text=self.text, justify='left',
                         background='#ffffe0', relief='solid', borderwidth=1)
        label.pack(ipadx=1)

    def leave(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

def load_prompts():
    """Load prompts from presets.json, create from template if needed."""
    prompts = []
    presets_path = os.path.join(SCRIPT_DIR, 'presets.json')
    template_path = os.path.join(SCRIPT_DIR, 'presets.json.template')
    
    try:
        # If presets.json doesn't exist, copy from template
        if not os.path.exists(presets_path) and os.path.exists(template_path):
            import shutil
            shutil.copy2(template_path, presets_path)
            print(strings.get('messages.console.presets.created', file=presets_path))
        
        # Load and parse the JSON file
        if os.path.exists(presets_path):
            with open(presets_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'presets' in data:
                    prompts = [(p['title'], p['text']) for p in data['presets'] 
                              if 'title' in p and 'text' in p]
        
        if not prompts:
            print(strings.get('messages.console.presets.warning'))
            # Add a default preset
            prompts = [("Basic Description", "What's in this image?")]
    except Exception as e:
        print(strings.get('messages.errors.load_presets', error=str(e)))
        # Add a default preset
        prompts = [("Basic Description", "What's in this image?")]
    
    return prompts

def save_settings():
    """Save current settings to .env file."""
    env_path = os.path.join(SCRIPT_DIR, '.env')
    set_key(env_path, 'BATCH_PROCESSING_ENABLED', str(batch_var.get()).lower())
    set_key(env_path, 'SAVE_INDIVIDUAL_ENABLED', str(save_individual_var.get()).lower())
    set_key(env_path, 'SAVE_LOCAL_IN_PLACE', str(save_local_var.get()).lower())
    set_key(env_path, 'OVERWRITE_FILES', str(overwrite_var.get()).lower())
    set_key(env_path, 'MAX_RESOLUTION', resolution_var.get())
    set_key(env_path, 'CURRENT_TIER', tier_var.get())
    set_key(env_path, 'LAST_USED_PROMPT', instructions_entry.get("1.0", "end-1c").strip())

def load_settings():
    """Load settings from .env file."""
    batch_enabled = os.getenv('BATCH_PROCESSING_ENABLED', 'false').lower() == 'true'
    batch_var.set(batch_enabled)
    
    save_individual_enabled = os.getenv('SAVE_INDIVIDUAL_ENABLED', 'true').lower() == 'true'
    save_individual_var.set(save_individual_enabled)
    
    save_local_enabled = os.getenv('SAVE_LOCAL_IN_PLACE', 'false').lower() == 'true'
    save_local_var.set(save_local_enabled)
    
    overwrite_enabled = os.getenv('OVERWRITE_FILES', 'true').lower() == 'true'
    overwrite_var.set(overwrite_enabled)
    
    max_resolution = os.getenv('MAX_RESOLUTION', '1024')
    resolution_var.set(max_resolution)
    
    current_tier = os.getenv('CURRENT_TIER', 'Free')
    tier_var.set(current_tier)
    
    last_prompt = os.getenv('LAST_USED_PROMPT', '')
    if last_prompt:
        instructions_entry.delete("1.0", tk.END)
        instructions_entry.insert("1.0", last_prompt)
    
    # Update dependent UI states
    update_save_options()

def get_credentials():
    return os.getenv('OPENAI_API_KEY')

def get_rate_limits():
    current_tier = os.getenv('CURRENT_TIER', 'Free')
    
    # Build tiers dictionary from environment variables
    tiers = {}
    tier_names = {
        'FREE': 'Free',
        '1': 'Tier 1',
        '2': 'Tier 2',
        '3': 'Tier 3',
        '4': 'Tier 4',
        '5': 'Tier 5'
    }
    
    for env_tier, display_name in tier_names.items():
        prefix = f'TIER_{env_tier}_'
        if os.getenv(f'{prefix}RPM'):
            tiers[display_name] = {
                'rpm': int(os.getenv(f'{prefix}RPM', 0)),
                'rpd': int(os.getenv(f'{prefix}RPD', 0)),
                'tpm': int(os.getenv(f'{prefix}TPM', 0)),
                'batch_limit': int(os.getenv(f'{prefix}BATCH_LIMIT', 0))
            }
    
    return current_tier, tiers

# Function to configure and get the OpenAI client
def get_openai_client():
    api_key = get_credentials()
    client = OpenAI(api_key=api_key)
    return client

# Function to read plain URLs from text area
def extract_image_urls(raw_text):
    urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return urls

def encode_image_file(image_path):
    """Process and encode an image file to base64, with resizing if needed."""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Get target resolution
            target_size = int(resolution_var.get())
            
            # Calculate scaling based on longest edge
            longest_edge = max(img.width, img.height)
            if longest_edge > target_size:
                scale_factor = target_size / longest_edge
                new_size = (
                    int(img.width * scale_factor),
                    int(img.height * scale_factor)
                )
                img = img.resize(new_size, Image.LANCZOS)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        raise ValueError(strings.get('messages.errors.image_processing.failed_to_process', error=str(e)))

def is_url(path):
    """Check if the path is a URL."""
    return path.startswith(('http://', 'https://', 'ftp://'))

def analyze_image(image_url, instruction_text, status_callback=None):
    # Global declarations
    global consecutive_errors, failed_files, total_prompt_tokens, total_completion_tokens, total_tokens
    
    try:
        client = get_openai_client()
        if status_callback:
            status_callback(strings.get('messages.processing.status.processing', file=image_url))
            
        # Prepare the image content based on whether it's a URL or local file
        if is_url(image_url):
            image_content = {
                "type": "image_url",
                "image_url": {"url": image_url}
            }
        else:
            # For local files, use base64 encoding
            base64_image = encode_image_file(image_url)
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction_text},
                        image_content
                    ],
                }
            ],
            max_tokens=300,
        )
    
        description = response.choices[0].message.content.strip()
        
        # Update token counts
        usage = response.usage
        total_prompt_tokens += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
        total_tokens += usage.total_tokens
        
        # Check for error responses
        error_patterns = strings.get('messages.errors.responses.patterns')
        if any(description.startswith(err) for err in error_patterns):
            error_msg = strings.get('messages.errors.api_error', message=description)
            print(strings.get('messages.errors.processing_error', file=image_url, error=error_msg))
            raise ValueError(error_msg)
        
        if status_callback:
            status_callback(strings.get('messages.processing.status.completed', file=image_url))
            
        # Reset consecutive errors on success
        consecutive_errors = 0
        
        return description
        
    except Exception as e:
        error_msg = str(e)
        print(strings.get('messages.errors.processing_error', file=image_url, error=error_msg))
        
        if status_callback:
            status_callback(strings.get('messages.processing.status.error', file=image_url, error=error_msg))
            
        # Track consecutive errors
        consecutive_errors += 1
        failed_files.append((image_url, error_msg))
        
        # Check if we should abort
        if MAX_CONSECUTIVE_ERRORS > 0 and consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            raise RuntimeError(strings.get('messages.errors.abort', count=MAX_CONSECUTIVE_ERRORS))
            
        return None

def write_to_file(description, filename, folder_path, original_path=None):
    """Write caption to file, either in the dated folder or next to the original file."""
    if not save_individual_var.get():
        # When individual captions are disabled, append to a consolidated file
        consolidated_path = os.path.join(folder_path, 'captions.txt')
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(consolidated_path, 'a', encoding='utf-8') as file:
            file.write(f"=== {filename} ===\n{description}\n\n")
        return

    # Individual caption files
    if original_path and save_local_var.get() and os.path.exists(original_path):
        # Save next to original file
        file_dir = os.path.dirname(original_path)
        file_path = os.path.join(file_dir, f'{filename}.txt')
    else:
        # Save in dated folder
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = os.path.join(folder_path, f'{filename}.txt')
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(description)

def update_save_options():
    """Update save options based on dependencies."""
    if not save_individual_var.get():
        save_local_var.set(False)
        save_local_checkbox.state(['disabled'])
        overwrite_checkbox.state(['disabled'])
    else:
        save_local_checkbox.state(['!disabled'])
        if save_local_var.get():
            overwrite_checkbox.state(['!disabled'])
        else:
            overwrite_var.set(False)
            overwrite_checkbox.state(['disabled'])
    save_settings()

def process_images(image_urls, instruction_text, folder_path, batch_mode=False, status_callback=None):
    global consecutive_errors, failed_files, total_prompt_tokens, total_completion_tokens, total_tokens
    consecutive_errors = 0
    failed_files = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    
    pbar = tqdm(total=total_images, desc="Processing images", unit="img")
    
    try:
        if batch_mode:
            # Get current tier limits
            current_tier, tiers = get_rate_limits()
            tier_limits = tiers[current_tier]
            
            # Calculate optimal number of workers based on RPM
            max_workers = min(tier_limits['rpm'], 10)  # Cap at 10 parallel workers
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for image_url in image_urls:
                    future = executor.submit(
                        analyze_image,
                        image_url,
                        instruction_text,
                        status_callback
                    )
                    futures.append((image_url, future))
                    
                # Process results as they complete
                for image_url, future in futures:
                    try:
                        description = future.result()
                        if description is not None:
                            filename = os.path.basename(image_url)
                            filename = urllib.parse.unquote(filename)
                            filename = os.path.splitext(filename)[0]
                            
                            # Save individual file
                            write_to_file(description, filename, folder_path, image_url if not is_url(image_url) else None)
                        
                        # Update progress regardless of success
                        increment_progress()
                        pbar.update(1)
                        
                    except Exception as e:
                        if status_callback:
                            status_callback(strings.get('messages.processing.status.error', file=image_url, error=str(e)))
                        
                        # Check if we should abort
                        if MAX_CONSECUTIVE_ERRORS > 0 and consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            raise RuntimeError(strings.get('messages.errors.abort', count=MAX_CONSECUTIVE_ERRORS))
        else:
            # Original sequential processing
            for image_url in image_urls:
                if status_callback:
                    status_callback(strings.get('messages.processing.status.processing', file=image_url))
                    
                try:
                    description = analyze_image(image_url, instruction_text, status_callback)
                    if description is not None:
                        filename = os.path.basename(image_url)
                        filename = urllib.parse.unquote(filename)
                        filename = os.path.splitext(filename)[0]
                        
                        # Save individual file
                        write_to_file(description, filename, folder_path, image_url if not is_url(image_url) else None)
                    
                    # Update progress regardless of success
                    increment_progress()
                    pbar.update(1)
                    
                except Exception as e:
                    if status_callback:
                        status_callback(strings.get('messages.processing.status.error', file=image_url, error=str(e)))
                    
                    # Check if we should abort
                    if MAX_CONSECUTIVE_ERRORS > 0 and consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        raise RuntimeError(strings.get('messages.errors.abort', count=MAX_CONSECUTIVE_ERRORS))
    
    finally:
        pbar.close()
        
        # Calculate token costs
        input_cost = total_prompt_tokens * TOKEN_COST_INPUT
        output_cost = total_completion_tokens * TOKEN_COST_OUTPUT
        total_cost = input_cost + output_cost
        
        # Format costs before string formatting
        input_cost_str = "{:.4f}".format(input_cost)
        output_cost_str = "{:.4f}".format(output_cost)
        total_cost_str = "{:.4f}".format(total_cost)
        
        # Print token usage and cost summary to console
        print(strings.get('messages.console.token_usage.header'))
        print(strings.get('messages.console.token_usage.input', count=total_prompt_tokens))
        print(strings.get('messages.console.token_usage.output', count=total_completion_tokens))
        print(strings.get('messages.console.token_usage.total', count=total_tokens))
        print(strings.get('messages.console.token_usage.cost.header'))
        print(strings.get('messages.console.token_usage.cost.input', cost=input_cost_str))
        print(strings.get('messages.console.token_usage.cost.output', cost=output_cost_str))
        print(strings.get('messages.console.token_usage.cost.total', cost=total_cost_str))
        
        # Print error summary to console
        if failed_files:
            print(strings.get('messages.console.errors.header'))
            print(strings.get('messages.console.errors.total', count=len(failed_files)))
            print(strings.get('messages.console.errors.details_header'))
            for file_path, error in failed_files:
                print(strings.get('messages.console.errors.file_prefix') + file_path)
                print(strings.get('messages.console.errors.error_prefix') + error)
            print("\n" + "="*50 + "\n")

def validate_images(all_images):
    """Validate image files and return statistics."""
    total_attempted = len(all_images)
    to_process = []
    ignored = []
    not_found = []
    
    for image_url in all_images:
        if is_url(image_url):
            to_process.append(image_url)
        else:
            # Check if file exists
            if not os.path.exists(image_url):
                not_found.append(image_url)
                continue
                
            # Check if output file exists and should be skipped
            if save_local_var.get() and not overwrite_var.get():
                filename = os.path.basename(image_url)
                filename = urllib.parse.unquote(filename)
                filename = os.path.splitext(filename)[0]
                file_dir = os.path.dirname(image_url)
                file_path = os.path.join(file_dir, f'{filename}.txt')
                
                if os.path.exists(file_path):
                    ignored.append(image_url)
                    continue
            
            to_process.append(image_url)
    
    # Print validation results to console
    print(strings.get('messages.console.validation.header'))
    print(strings.get('messages.console.validation.total', total=total_attempted))
    print(strings.get('messages.console.validation.to_process', count=len(to_process)))
    
    if ignored:
        print(strings.get('messages.console.validation.skipped_header'))
        for f in ignored:
            print(strings.get('messages.console.validation.file_prefix') + f)
            
    if not_found:
        print(strings.get('messages.console.validation.not_found_header'))
        for f in not_found:
            print(strings.get('messages.console.validation.file_prefix') + f)
    
    print("\n" + "="*50 + "\n")
    
    return {
        'total_attempted': total_attempted,
        'to_process': to_process,
        'ignored': ignored,
        'not_found': not_found
    }

def estimate_cost(number_of_images, instruction_text, image_urls):
    # Get base cost per image based on resolution
    resolution = int(resolution_var.get())
    if resolution == 2048:
        cost_per_image = 0.00563
    elif resolution == 1024:
        cost_per_image = 0.00393
    else:  # 512
        cost_per_image = 0.00138
    
    # Calculate base vision processing cost
    total_vision_processing_cost = number_of_images * cost_per_image

    # Additional token-based cost calculation
    cost_per_1K_output_tokens = 0.03  # $0.03 per 1K tokens for output
    cost_per_1K_input_tokens = 0.01   # $0.01 per 1K tokens for input

    # Calculate total input length from instruction text and image URLs
    total_input_text = instruction_text + " ".join(image_urls)
    total_input_tokens = len(total_input_text) / 4  # Rough estimate of token count

    # Assume an average output token count per image
    average_output_tokens_per_image = 120
    total_output_tokens = average_output_tokens_per_image * number_of_images

    # Calculate total cost for input and output tokens
    total_input_token_cost = (total_input_tokens / 1000) * cost_per_1K_input_tokens
    total_output_token_cost = (total_output_tokens / 1000) * cost_per_1K_output_tokens

    # Sum up all costs
    total_cost = total_vision_processing_cost + total_input_token_cost + total_output_token_cost

    # Add a custom % additional cost. Magic number to be more accurate
    if resolution == 2048:
        total_cost *= 0.55
    elif resolution == 1024:
        total_cost *= 0.45
    else:  # 512
        total_cost *= 0.3

    return total_cost

def generate_captions():
    # Get web URLs
    web_text = web_text_area.get("1.0", tk.END).strip()
    if web_text == strings.get('ui.web_urls.placeholder'):
        web_urls = []
    else:
        web_urls = extract_image_urls(web_text)
    
    # Get local files
    local_text = local_text_area.get("1.0", tk.END).strip()
    if local_text == strings.get('ui.local_files.placeholder'):
        local_files = []
    else:
        local_files = extract_image_urls(local_text)

    # Combine URLs and files
    all_images = web_urls + local_files
    
    if not all_images:
        messagebox.showerror(
            strings.get('messages.dialogs.error.title'),
            strings.get('messages.validation.no_images')
        )
        return

    # Validate images
    validation = validate_images(all_images)
    if not validation['to_process']:
        messagebox.showerror(
            strings.get('messages.dialogs.error.title'),
            strings.get('messages.validation.no_valid_images')
        )
        return
        
    # Build validation message
    validation_msg = strings.get('messages.validation.summary',
        total=validation['total_attempted'],
        to_process=len(validation['to_process'])
    )
    
    if validation['ignored']:
        validation_msg += strings.get('messages.validation.skipped',
            count=len(validation['ignored'])
        )
        
    if validation['not_found']:
        validation_msg += strings.get('messages.validation.not_found',
            count=len(validation['not_found'])
        )
    
    instruction_text = instructions_entry.get("1.0", "end-1c").strip()

    # Calculate the estimated cost including token-based costs
    cost = estimate_cost(len(validation['to_process']), instruction_text, validation['to_process'])

    # Format the cost string with 4 decimal places instead of 2
    cost_str = "{:.4f}".format(cost)

    # Ask the user if they want to proceed with the estimated cost
    proceed = messagebox.askyesno(
        strings.get('messages.dialogs.validation.title'),
        strings.get('messages.dialogs.validation.message',
            validation=validation_msg,
            count=len(validation['to_process']),
            cost=cost_str
        )
    )
    
    if proceed:
        print(strings.get('messages.processing.start', count=len(validation['to_process'])))
        # Update the UI to indicate processing
        generate_button.config(text=strings.get('ui.generate.processing_text'), state="disabled")

        date_folder = datetime.datetime.now().strftime('%Y-%m-%d')
        global time_folder  # Declare time_folder as global to use in the threaded function
        time_folder = datetime.datetime.now().strftime('%Y-%m-%d - %H.%M.%S')
        
        # Get the root directory (parent of scripts)
        root_dir = os.path.dirname(SCRIPT_DIR)
        output_folder = os.path.join(root_dir, 'output', date_folder, time_folder)

        # Create and start a new thread for the process_images function
        threading.Thread(
            target=threaded_process_images,
            args=(validation['to_process'], instruction_text, output_folder, batch_var.get()),
            daemon=True
        ).start()
    else:
        messagebox.showinfo(
            strings.get('messages.dialogs.cancelled.title'),
            strings.get('messages.dialogs.cancelled.message')
        )

# GUI setup
root = TkinterDnD.Tk()  # Use TkinterDnD.Tk instead of tk.Tk
root.title(strings.get('ui.window.title'))

# Add window closing handler
def on_closing():
    save_settings()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Main window size, width and height
root.geometry("1000x700")

# Main container with padding
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Web URLs Frame
web_frame = ttk.LabelFrame(main_frame, text=strings.get('ui.web_urls.frame_title'), padding="5")
web_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

# Web URLs text area with scrollbar
web_scroll = ttk.Scrollbar(web_frame)
web_scroll.pack(side=tk.RIGHT, fill=tk.Y)

web_text_area = tk.Text(web_frame, height=6, yscrollcommand=web_scroll.set)
web_text_area.pack(fill=tk.BOTH, expand=True, pady=5)
web_text_area.insert("1.0", strings.get('ui.web_urls.placeholder'))
web_text_area.configure(fg='gray')
web_scroll.config(command=web_text_area.yview)

def on_web_focus_in(event):
    if web_text_area.get("1.0", "end-1c") == strings.get('ui.web_urls.placeholder'):
        web_text_area.delete("1.0", "end")
        web_text_area.configure(fg='black')

def on_web_focus_out(event):
    if not web_text_area.get("1.0", "end-1c").strip():
        web_text_area.insert("1.0", strings.get('ui.web_urls.placeholder'))
        web_text_area.configure(fg='gray')

web_text_area.bind('<FocusIn>', on_web_focus_in)
web_text_area.bind('<FocusOut>', on_web_focus_out)

# Local Files Frame
local_frame = ttk.LabelFrame(main_frame, text=strings.get('ui.local_files.frame_title'), padding="5")
local_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

# Local files text area with scrollbar
local_scroll = ttk.Scrollbar(local_frame)
local_scroll.pack(side=tk.RIGHT, fill=tk.Y)

local_text_area = tk.Text(local_frame, height=6, yscrollcommand=local_scroll.set)
local_text_area.pack(fill=tk.BOTH, expand=True, pady=5)
local_text_area.insert("1.0", strings.get('ui.local_files.placeholder'))
local_text_area.configure(fg='gray')
local_scroll.config(command=local_text_area.yview)

def on_local_focus_in(event):
    if local_text_area.get("1.0", "end-1c") == strings.get('ui.local_files.placeholder'):
        local_text_area.delete("1.0", "end")
        local_text_area.configure(fg='black')

def on_local_focus_out(event):
    if not local_text_area.get("1.0", "end-1c").strip():
        local_text_area.insert("1.0", strings.get('ui.local_files.placeholder'))
        local_text_area.configure(fg='gray')

local_text_area.bind('<FocusIn>', on_local_focus_in)
local_text_area.bind('<FocusOut>', on_local_focus_out)

def handle_drop(event):
    # Get the dropped files
    files = event.data
    if files:
        # Convert the dropped data to a list of files
        if isinstance(files, str):
            files = root.tk.splitlist(files)
        
        # Filter for image files
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
        image_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_extensions]
        
        if image_files:
            # Get current text if it's not the placeholder
            current_text = local_text_area.get("1.0", tk.END).strip()
            if current_text == strings.get('ui.local_files.placeholder'):
                current_files = set()
            else:
                current_files = set(current_text.split("\n") if current_text else [])
            
            # Add new files
            current_files.update(image_files)
            
            # Update text area with absolute paths
            local_text_area.delete("1.0", tk.END)
            local_text_area.insert("1.0", "\n".join(sorted(os.path.abspath(f) for f in current_files)))
            local_text_area.configure(fg='black')

# Enable drag and drop
local_text_area.drop_target_register(DND_FILES)
local_text_area.dnd_bind('<<Drop>>', handle_drop)

# Local files buttons
local_button_frame = ttk.Frame(local_frame)
local_button_frame.pack(fill=tk.X)

def browse_files():
    files = filedialog.askopenfilenames(
        title=strings.get('ui.local_files.dialog_title'),
        filetypes=[
            (strings.get('ui.local_files.file_types.images'), "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
            (strings.get('ui.local_files.file_types.all'), "*.*")
        ]
    )
    if files:
        # Get current text if it's not the placeholder
        current_text = local_text_area.get("1.0", tk.END).strip()
        if current_text == strings.get('ui.local_files.placeholder'):
            current_files = set()
        else:
            current_files = set(current_text.split("\n") if current_text else [])
        
        # Add new files
        current_files.update(files)
        
        # Update text area with absolute paths
        local_text_area.delete("1.0", tk.END)
        local_text_area.insert("1.0", "\n".join(sorted(os.path.abspath(f) for f in current_files)))
        local_text_area.configure(fg='black')

ttk.Button(
    local_button_frame,
    text=strings.get('ui.local_files.browse_button'),
    command=browse_files
).pack(side=tk.LEFT, padx=5)

ttk.Button(
    local_button_frame,
    text=strings.get('ui.local_files.clear_button'),
    command=lambda: (local_text_area.delete("1.0", tk.END), on_local_focus_out(None))
).pack(side=tk.LEFT)

# Processing Options Frame
options_frame = ttk.LabelFrame(main_frame, text=strings.get('ui.options.frame_title'), padding="5")
options_frame.pack(fill=tk.X, pady=(0, 10))

# Left side options (Save options)
left_options = ttk.Frame(options_frame)
left_options.pack(side=tk.LEFT, fill=tk.X, expand=True)

# Save options
save_individual_var = tk.BooleanVar(value=True)
save_individual_checkbox = ttk.Checkbutton(
    left_options,
    text=strings.get('ui.options.save_individual.text'),
    variable=save_individual_var,
    command=update_save_options
)
CreateToolTip(save_individual_checkbox, strings.get('ui.options.save_individual.tooltip'))
save_individual_checkbox.pack(side=tk.LEFT, padx=5)

save_local_var = tk.BooleanVar(value=False)
save_local_checkbox = ttk.Checkbutton(
    left_options,
    text=strings.get('ui.options.save_local.text'),
    variable=save_local_var,
    command=update_save_options
)
CreateToolTip(save_local_checkbox, strings.get('ui.options.save_local.tooltip'))
save_local_checkbox.pack(side=tk.LEFT, padx=5)

overwrite_var = tk.BooleanVar(value=True)
overwrite_checkbox = ttk.Checkbutton(
    left_options,
    text=strings.get('ui.options.overwrite.text'),
    variable=overwrite_var,
    command=update_save_options
)
CreateToolTip(overwrite_checkbox, strings.get('ui.options.overwrite.tooltip'))
overwrite_checkbox.pack(side=tk.LEFT, padx=5)

# Right side options (Batch Processing and Tier selection)
right_options = ttk.Frame(options_frame)
right_options.pack(side=tk.RIGHT, fill=tk.X)

# Resolution dropdown
resolution_var = tk.StringVar(value="1024")
resolution_label = ttk.Label(right_options, text=strings.get('ui.options.resolution.label'))
resolution_label.pack(side=tk.LEFT, padx=(5, 0))
CreateToolTip(resolution_label, strings.get('ui.options.resolution.tooltip'))

resolution_dropdown = ttk.Combobox(
    right_options,
    textvariable=resolution_var,
    values=["512", "1024", "2048"],
    state="readonly",
    width=6
)
CreateToolTip(resolution_dropdown, strings.get('ui.options.resolution.tooltip'))
resolution_dropdown.pack(side=tk.LEFT, padx=5)
resolution_dropdown.bind('<<ComboboxSelected>>', lambda e: save_settings())

# Batch processing toggle
batch_var = tk.BooleanVar(value=False)
batch_checkbox = ttk.Checkbutton(
    right_options,
    text=strings.get('ui.options.batch.text'),
    variable=batch_var,
    command=save_settings
)
CreateToolTip(batch_checkbox, strings.get('ui.options.batch.tooltip'))
batch_checkbox.pack(side=tk.LEFT, padx=5)

# Get current tier and available tiers
current_tier, tiers = get_rate_limits()
tier_var = tk.StringVar(value=current_tier)

tier_label = ttk.Label(right_options, text=strings.get('ui.options.tier.label'))
tier_label.pack(side=tk.LEFT, padx=(10, 0))
CreateToolTip(tier_label, strings.get('ui.options.tier.tooltip'))

tier_dropdown = ttk.Combobox(
    right_options,
    textvariable=tier_var,
    values=list(tiers.keys()),
    state="readonly",
    width=10
)
tier_dropdown.pack(side=tk.LEFT, padx=5)
CreateToolTip(tier_dropdown, strings.get('ui.options.tier.tooltip'))

def update_tier(event=None):
    set_key(os.path.join(SCRIPT_DIR, '.env'), 'CURRENT_TIER', tier_var.get())
    save_settings()

tier_dropdown.bind('<<ComboboxSelected>>', update_tier)

# Instructions Frame
instructions_frame = ttk.LabelFrame(main_frame, text=strings.get('ui.instructions.frame_title'), padding="5")
instructions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

# Prompt Library Dropdown
prompts = load_prompts()
prompt_var = tk.StringVar(value=strings.get('ui.instructions.prompt_default'))

def update_prompt(*args):
    selected = prompt_var.get()
    for title, text in prompts:
        if title == selected:
            instructions_entry.delete("1.0", tk.END)
            instructions_entry.insert("1.0", text)
            save_settings()
            break

prompt_dropdown = ttk.Combobox(
    instructions_frame,
    textvariable=prompt_var,
    values=[title for title, _ in prompts],
    state="readonly",
    width=40
)
prompt_dropdown.pack(fill=tk.X, pady=(0, 5))
prompt_dropdown.bind('<<ComboboxSelected>>', update_prompt)

instructions_scroll = ttk.Scrollbar(instructions_frame)
instructions_scroll.pack(side=tk.RIGHT, fill=tk.Y)

instructions_entry = tk.Text(instructions_frame, height=6, yscrollcommand=instructions_scroll.set)
instructions_entry.pack(fill=tk.BOTH, expand=True, pady=5)
instructions_scroll.config(command=instructions_entry.yview)

# Generate button frame
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=(0, 10))

# Generate button with increased height
style = ttk.Style()
style.configure('Tall.TButton', padding=10)
generate_button = ttk.Button(
    button_frame,
    text=strings.get('ui.generate.button_text'),
    command=generate_captions,
    style='Tall.TButton'
)
generate_button.pack(fill=tk.X)

# Status frame with progress bar
status_frame = ttk.Frame(main_frame)
status_frame.pack(fill=tk.X, pady=(0, 10))

# Progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(
    status_frame,
    variable=progress_var,
    maximum=100,
    mode='determinate'
)
progress_bar.pack(fill=tk.X, pady=(0, 5))

# Status label
status_label = ttk.Label(status_frame, text="")
status_label.pack(fill=tk.X)

def threaded_process_images(image_urls, instruction_text, output_folder, batch_mode):
    """Process images in a separate thread to keep UI responsive."""
    global total_images, processed_images
    total_images = len(image_urls)
    processed_images = 0
    update_progress()
    
    try:
        # Process images with status updates
        process_images(
            image_urls,
            instruction_text,
            output_folder,
            batch_mode,
            status_callback=update_status
        )
        
        update_status(strings.get('messages.processing.complete'))
        
        # Update the UI after processing is complete
        def update_ui():
            generate_button.config(text=strings.get('ui.generate.button_text'), state="normal")
            
            # Calculate token costs
            input_cost = total_prompt_tokens * TOKEN_COST_INPUT
            output_cost = total_completion_tokens * TOKEN_COST_OUTPUT
            total_cost = input_cost + output_cost
            
            # Format costs before string formatting
            input_cost_str = "{:.4f}".format(input_cost)
            output_cost_str = "{:.4f}".format(output_cost)
            total_cost_str = "{:.4f}".format(total_cost)
            
            # Build completion message
            msg = strings.get('messages.dialogs.results.message',
                processed=processed_images,
                input=total_prompt_tokens,
                output=total_completion_tokens,
                total=total_tokens,
                input_cost=f"${input_cost_str}",
                output_cost=f"${output_cost_str}",
                total_cost=f"${total_cost_str}"
            )
            
            if failed_files:
                msg += strings.get('messages.errors.group.header', count=len(failed_files))
                # Group similar errors together
                error_groups = {}
                for file_path, error in failed_files:
                    if error not in error_groups:
                        error_groups[error] = []
                    error_groups[error].append(os.path.basename(file_path))
                
                # Show errors grouped by type
                for error, files in error_groups.items():
                    msg += strings.get('messages.errors.group.error_header', error=error)
                    msg += strings.get('messages.errors.group.files_header')
                    files_str = strings.get('messages.errors.group.file_prefix').join(files[:5])
                    msg += strings.get('messages.errors.group.file_prefix') + files_str
                    if len(files) > 5:
                        msg += strings.get('messages.errors.group.more_files', count=len(files) - 5)
            
            if MAX_CONSECUTIVE_ERRORS > 0 and consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                msg += strings.get('messages.errors.abort', count=MAX_CONSECUTIVE_ERRORS)
            
            messagebox.showinfo(strings.get('messages.dialogs.results.title'), msg)
            
        root.after(0, update_ui)
        
    except Exception as e:
        error_msg = str(e)
        update_status(strings.get('messages.processing.status.error', file="", error=error_msg))
        
        def show_error():
            generate_button.config(text=strings.get('ui.generate.button_text'), state="normal")
            
            # Calculate token costs
            input_cost = total_prompt_tokens * TOKEN_COST_INPUT
            output_cost = total_completion_tokens * TOKEN_COST_OUTPUT
            total_cost = input_cost + output_cost
            
            # Format costs before string formatting
            input_cost_str = "{:.4f}".format(input_cost)
            output_cost_str = "{:.4f}".format(output_cost)
            total_cost_str = "{:.4f}".format(total_cost)
            
            # Build error message
            msg = strings.get('messages.dialogs.error.message',
                error=error_msg,
                processed=processed_images,
                input=total_prompt_tokens,
                output=total_completion_tokens,
                total=total_tokens,
                input_cost=f"${input_cost_str}",
                output_cost=f"${output_cost_str}",
                total_cost=f"${total_cost_str}"
            )
            
            if failed_files:
                msg += strings.get('messages.errors.group.header', count=len(failed_files))
                # Group similar errors together
                error_groups = {}
                for file_path, error in failed_files:
                    if error not in error_groups:
                        error_groups[error] = []
                    error_groups[error].append(os.path.basename(file_path))
                
                # Show errors grouped by type
                for error, files in error_groups.items():
                    msg += strings.get('messages.errors.group.error_header', error=error)
                    msg += strings.get('messages.errors.group.files_header')
                    files_str = strings.get('messages.errors.group.file_prefix').join(files[:5])
                    msg += strings.get('messages.errors.group.file_prefix') + files_str
                    if len(files) > 5:
                        msg += strings.get('messages.errors.group.more_files', count=len(files) - 5)
            
            messagebox.showerror(strings.get('messages.dialogs.error.title'), msg)
            
        root.after(0, show_error)

# Load settings after all UI elements are created
load_settings()

root.mainloop()