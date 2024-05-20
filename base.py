import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from io import BytesIO
import requests, base64
from PIL import Image, ImageDraw, ImageFont
import replicate
import re
import textwrap
from base64 import b64decode

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

os.environ["REPLICATE_API_TOKEN"] = ""

@app.route("/")
@cross_origin()
def helloWorld():
  return "Hello, cross-origin-world!"

""" url = "http://127.0.0.1:7860"
opt = requests.get(url=f'{url}/sdapi/v1/options')
opt_json = opt.json()
opt_json['sd_model_checkpoint'] = 'sd1.5 Poster generator.safetensors'
requests.post(url=f'{url}/sdapi/v1/options', json=opt_json)
 """


def encode_img_to_b64(image_path):
    binary_fc = open(image_path, 'rb').read()  
    base64_utf8_str = base64.b64encode(binary_fc).decode('utf-8')
    ext = image_path.split('.')[-1]
    dataurl = f'data:image/{ext};base64,{base64_utf8_str}'
    return dataurl

client = replicate.Client()
print(client._api_token)

false = False
true = True

def generateContent(prompt):
    output1 = replicate.run(
    "meta/llama-2-7b-chat:f1d50bb24186c52daae319ca8366e53debdaa9e0ae7ff976e918df752732ccc4",
    input={
        "prompt": "write a post for " + prompt,
        "system_prompt": "You are made to assist in marketing content writing in 100 words and only replies with the answer.",
        "max_new_tokens": 128,
        "min_new_tokens": -1,
        })  
    content = output1
    contentString = ""
    for item in content:
        contentString = contentString + item

    contentString = contentString.replace('"', '')
    print(contentString)
    return contentString

def addCaption(prompt, template):

    output = replicate.run(
    "meta/llama-2-7b-chat:f1d50bb24186c52daae319ca8366e53debdaa9e0ae7ff976e918df752732ccc4",
    input={
        "prompt": "write a tagline for " + prompt,
        "system_prompt": "You are made to assist marketing and content writing and only replies with the answer.",
        "max_new_tokens": 128,
        "min_new_tokens": -1,
        }
    )

    image = Image.open(template)

    caption = output
    captionString = ""
    for item in caption:
        captionString = captionString + item

    captionString = captionString.replace('"', '')
    print(captionString)
    print("adding caption")
    

    font = ImageFont.truetype("arial.ttf", 30)
    draw = ImageDraw.Draw(image)

    x = image.width
    y = image.height - (image.height / 4)

    wrapwidth = x / 4

    wrapper = textwrap.TextWrapper(width=25) 
    word_list = wrapper.wrap(text=captionString) 
    wrapped_text = ''

    for ii in word_list[:-1]:
        wrapped_text = wrapped_text + ii + '\n'
    wrapped_text += word_list[-1]


    draw.text(
        xy=(x / 2, y),
        text=wrapped_text,
        fill="#000000",
        font=font,
        anchor="mm",
        align="center"
    )
    image.save("output_image.png")

def addLogoText(Text):
    logoTemplate = Image.open("./controlnetinputs/logotemplate.png")
    font = ImageFont.truetype("COOPBL.TTF", 50)
    draw = ImageDraw.Draw(logoTemplate)
    x = logoTemplate.width / 2
    y = logoTemplate.height / 2

    draw.text((x, y), text=Text, font=font, fill="#000000", anchor="mm", align="center")
    logoTemplate.save("logo_output.png")

@app.route("/getColors", methods=['GET'])
def getColors():
    output = replicate.run(
    "meta/llama-2-7b-chat:f1d50bb24186c52daae319ca8366e53debdaa9e0ae7ff976e918df752732ccc4",
    input={
        "top_k": 0,
        "top_p": 1,
        "prompt": "give me a material ui primary and secondary color",
        "temperature": 0.75,
        "system_prompt": "answer only with the hex and color name.",
        "length_penalty": 1,
        "max_new_tokens": 50,
        "prompt_template": "<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{prompt} [/INST]",
        "presence_penalty": 0
        }
    )

    textString = ""
    for item in output:
        textString = textString + item 
    print(textString)

    color_names = [match.strip("()") for match in re.findall(r"\(.*?\)", textString)]
    hex_colors = re.findall(r"#[\w]{6}", textString)

    r =  hex_colors + color_names
    return r

@app.route("/img2img", methods=['POST'])
def img2img():

    promptjson = request.get_json()
    prompt = promptjson['prompt']
    template = "./controlnetinputs/template1.png"

    print(promptjson)
    
    addCaption(prompt, template)
    
    content = generateContent(prompt)
    
    encoded_image = encode_img_to_b64('output_image.png') 

    output = replicate.run(
    "lucataco/sdxl-controlnet:06d6fae3b75ab68a28cd2900afa6033166910dd09fd9751047043a5bbb4c184b",
    input={
        "image": encoded_image,
        "prompt": "poster for " + prompt + ",advertisement, 4k",
        "condition_scale": 0.7,
        "negative_prompt": "low quality, bad quality, sketches, bad text, disfigured, disfigured text",
        "num_inference_steps": 35,
        "seed":0
    }
    )
    print(output) 

    img_data = requests.get(output).content
    with open('output.png', 'wb') as handler:
        handler.write(img_data)

    final_image = encode_img_to_b64('output.png')  

    Image = final_image
    response = {'imageData': Image, 'Textdata': content}
    return jsonify(response)


@app.route("/logo", methods=['POST'])
def logo():

    promptjson = request.get_json()
    prompt = promptjson['prompt']
    addLogoText(prompt)
    encoded_image = encode_img_to_b64('logo_output.png')

    payload = {
    "alwayson_scripts": {
        "ControlNet": {
            "args": [
                {
                    "control_mode": "Balanced",
                    "enabled": true,
                    "guidance_end": 0.8,
                    "guidance_start": 0.2,
                    "hr_option": "Both",
                    "input_image": encoded_image,
                    "input_mode": "simple",
                    "model": "control_v11p_sd15_canny [d14c016b]",
                    "module": "canny",
                    "pixel_perfect": true,
                    "processor_res": 512,
                    "resize_mode": "Crop and Resize",
                    "save_detected_map": false,
                    "threshold_a": 100,
                    "threshold_b": 200,
                    "weight": 1.5,
                },
            ]
        },
    },
    "batch_size": 1,
    "cfg_scale": 7,
    "disable_extra_networks": false,
    "do_not_save_grid": false,
    "do_not_save_samples": false,
    "enable_hr": false,
    "height": 512,
    "hr_negative_prompt": "",
    "hr_prompt": "",
    "hr_resize_x": 0,
    "hr_resize_y": 0,
    "hr_scale": 2,
    "hr_second_pass_steps": 0,
    "hr_upscaler": "Latent",
    "n_iter": 1,
    "negative_prompt": "",
    "override_settings": {},
    "override_settings_restore_afterwards": true,
    "prompt": prompt + ", stylish logo <lora:logo_v1-000012:1>",
    "sampler_name": "DPM++ 2M Karras",
    "seed": -1,
    "seed_enable_extras": true,
    "steps": 25,
    "subseed": -1,
    "subseed_strength": 0,
    "width": 512,
}

    response = requests.post('http://127.0.0.1:7860/sdapi/v1/txt2img', json=payload)
    r = response.json()
    return r




if __name__ == "__main__":
    app.run(debug=True)
