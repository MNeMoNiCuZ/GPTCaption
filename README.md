# GPTCaption
GPTCaption is a tool designed to leverage the ChatGPT API for generating captions that describe images. This application streamlines the process of obtaining descriptive captions for a variety of image formats.

# Example Captioning Results
This image showcases an example of the captioning capability of GPTCaption, demonstrating how the tool can provide contextually relevant descriptions for diverse types of images.

![image](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/623d9320-7210-43d5-aa69-3f81b05ff575)

# Usage
To utilize GPTCaption, follow these steps:

1. Enter your OpenAI API key into the `settings.ini` file to authenticate your requests.
2. Execute `main_gui.py` to launch the graphical user interface.
3. Insert the URLs of the images you wish to caption into the designated field, ensuring one URL per line. The tool currently supports images in JPG, JPEG, and PNG formats.
4. Optionally, you can modify the image analysis prompt to suit your specific needs or preferences.
5. Click on `Generate Captions` to initiate the captioning process.

Before proceeding with the API calls, GPTCaption will present an estimate of the potential costs involved and request your confirmation to continue.

The output, including all generated captions, will be organized in a folder named after the current date. Inside this folder, additional time-stamped subfolders are created for each use of the tool, with a consolidated caption file named identically to its corresponding folder.

![image](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/cad0056c-2670-47ec-b2ce-6cc4904badc0)

# Image Hosting
GPTCaption is compatible with any image hosting service that offers public URL access to the uploaded images. For batch uploading (up to 1000 images), https://PostImages.org is recommended. Ensure you select "Direct Link" as the URL type for compatibility with GPTCaption.
![image](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/76f95c8e-3d2c-4395-ad58-f3aa251a6602)
