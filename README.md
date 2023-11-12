# GPTCaption
A captioning tool using ChatGPT (API) to describe images.

# Example Captioning Results
![CaptionCompare](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/1aa9d4f6-36d6-4c60-b52a-99fbc1cbe0fd)


# Usage
1. Add your OpenAI API-key in the settings.ini-file.

2. Run main_gui.py.

3. Paste a bunch of URLs to images you wish to caption, one per line. Supports JPG, JPEG, PNG.

4. Optional: Edit the image analysis prompt.

5. Press Generate Captions

It will make a rough estimate of the API call costs and ask if you want to continue.

It will output everything in a date-folder, with an additional time-stamped folder each time you use the tool. Inside this folder there's also one caption with the same name as the folder that includes all captions.

![image](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/cad0056c-2670-47ec-b2ce-6cc4904badc0)

# Image Hosting
You can use any service as long as the URL is public.

You can upload a batch of images (max 1000) on https://PostImages.org and get a list of URLs.

Be sure to select "Direct Link" as URL type.
![image](https://github.com/MNeMoNiCuZ/GPTCaption/assets/60541708/76f95c8e-3d2c-4395-ad58-f3aa251a6602)
