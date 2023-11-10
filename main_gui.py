import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import configparser
import openai
import os
import datetime
from openai import OpenAI
import threading

# Define the get_credentials function in your script
def get_credentials():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    return config['openai']['api_key']

# Set the API key for openai
openai.api_key = get_credentials()

# Function to read plain URLs from text area
def extract_image_urls(raw_text):
    urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return urls

# Function to configure and get the OpenAI client
def get_openai_client():
    api_key = get_credentials()
    client = OpenAI(api_key=api_key)
    return client

def analyze_image(image_url):
    client = get_openai_client()
    print(f"Sending API request for image: {image_url}")  # Status message for API request
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What’s in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
    
        description = response.choices[0].message.content
        print(f"Received caption: {description}")  # Status message for API response
        return description.strip()
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while analyzing the image."

def write_to_file(description, filename, folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f'{filename}.txt')
    print(f"Writing caption to file: {os.path.join(folder_path, f'{filename}.txt')}")  # Status message for writing to file
    with open(file_path, 'w') as file:
        file.write(description)

def process_images(image_urls, folder_path):
    for image_url in image_urls:
        filename = os.path.basename(image_url).split('.')[0]
        description = analyze_image(image_url)
        write_to_file(description, filename, folder_path)

# GUI setup
root = tk.Tk()
root.title("Image Caption with ChatGPT API")
root.geometry("800x600")

url_label = tk.Label(root, text="Paste image URLs here (one per line):")
url_label.pack(fill='x')

url_text_area = scrolledtext.ScrolledText(root, height=8)
url_text_area.pack(fill='both', expand=True)
url_text_area.insert(tk.END, "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Pioneer_Building%2C_San_Francisco_%282019%29_-1.jpg/1920px-Pioneer_Building%2C_San_Francisco_%282019%29_-1.jpg")

instructions_label = tk.Label(root, text="Enter instructions for the image analysis:")
instructions_label.pack(fill='x')


instructions_entry = scrolledtext.ScrolledText(root, height=4)
instructions_entry.pack(fill='both', expand=True)
instructions_entry.insert(tk.END, "What's in this image?")

def generate_captions():
    raw_urls = url_text_area.get("1.0", tk.END)
    image_urls = extract_image_urls(raw_urls)
    instruction_text = instructions_entry.get("1.0", "end-1c").strip()  # Retrieve the instruction text

    if not image_urls:
        messagebox.showerror("Error", "No valid image URLs found. Please check the input.")
        return

    # Calculate the estimated cost including token-based costs
    cost = estimate_cost(len(image_urls), instruction_text, image_urls)

    # Ask the user if they want to proceed with the estimated cost
    proceed = messagebox.askyesno(
        "Estimated Cost",
        f"The estimated cost for analyzing (assuming each image is 1024x1024 and you did not enter a crazy instruction){len(image_urls)} images is ${cost:.2f}. Do you want to continue?"
    )
    if proceed:
        print(f"Starting the caption generation process for {len(image_urls)} images.")  # 
        # Update the UI to indicate processing
        generate_button.config(text="Processing...", state="disabled")

        date_folder = datetime.datetime.now().strftime('%Y-%m-%d')
        global time_folder  # Declare time_folder as global to use in the threaded function
        time_folder = datetime.datetime.now().strftime('%Y-%m-%d - %H.%M.%S')
        output_folder = os.path.join('captions', date_folder, time_folder)

        # Create and start a new thread for the process_images function
        threading.Thread(target=threaded_process_images, args=(image_urls, output_folder), daemon=True).start()
    else:
        messagebox.showinfo("Cancelled", "Image captioning was not processed.")

def threaded_process_images(image_urls, output_folder):
    all_descriptions = []  # List to hold all descriptions
    global time_folder  # Use the global time_folder variable

    # Process each image and collect descriptions
    for image_url in image_urls:
        filename = os.path.basename(image_url).split('.')[0]
        description = analyze_image(image_url)
        write_to_file(description, filename, output_folder)
        all_descriptions.append(f"Image: {image_url}\nCaption: {description}\n\n")  # Add image URL and description to list

    # Write all descriptions to a single file in the date folder
    combined_filename = f"{output_folder}{os.path.sep}{time_folder}.txt"  # Construct combined filename
    with open(combined_filename, 'w') as combined_file:
        combined_file.write("\n".join(all_descriptions))  # Write all descriptions to the file

    print(f"All captions have been combined into the file: {combined_filename}")  # Print status message

    # Update the UI after processing is complete
    def update_ui():
        generate_button.config(text="Generate Captions", state="normal")
        messagebox.showinfo("Success", f"Captions generated in folder: {output_folder}")
    root.after(0, update_ui)

def estimate_cost(number_of_images, instruction_text, image_urls):
    # Original fixed cost estimate
    cost_per_image = 0.00765  # $0.00765 per image for the actual vision processing
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
    return total_cost

# Ensure that the generate_button is created in the global scope so that it can be accessed in the threaded_process_images function
generate_button = tk.Button(root, text="Generate Captions", command=generate_captions)
generate_button.pack()

root.mainloop()