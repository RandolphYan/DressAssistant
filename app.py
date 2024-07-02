import os

from agentscope.message import Msg
from agentscope.msghub import msghub
import agentscope
from agentscope.agents.user_agent import UserAgent
# from agentscope.agents.dialog_agent import DialogAgent
from agentscope.agents.text_to_image_agent import TextToImageAgent
import gradio as gr
import requests
import concurrent.futures
from PIL import Image
import io


def get_weather():
    weather_key = '494d50b3bfe009cc5e0da51d25e6bff0'  # 每天50次调用额度, 尽量自己申请一个 https://dashboard.juhe.cn/data/index/my
    url = "http://apis.juhe.cn/simpleWeather/query"
    params = {
        'city': u'上海',
        'key': weather_key,
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data['error_code'] != 0:
        print('天气啊查询失败，原因：', data['reason'])
        return '未查询到当前天气'
    realtime_data = data['result']['realtime']
    realtime_str = '当前天气%s, 温度：%s℃, 湿度：%s%%, 风向：%s 风力：%s 空气质量：%s' % (
        realtime_data['info'], realtime_data['temperature'], realtime_data['humidity'], realtime_data['direct'],
        realtime_data['power'], realtime_data['aqi']
    )

    return realtime_str


weather = get_weather()
API_KEY = os.getenv('DASHSCOPE_API_KEY')

agentscope.init(
    model_configs=[
        {
            "config_name": "neuralchat_config",  # 配置名称，需要唯一
            "model_type": "openai_api",  # 模型类型，这里使用 post_api 表示 POST 请求的 API
            "api_url": "http://192.168.1.180:1611/v1/",  # 你的本地模型服务 URL
            "headers": {
                "Content-Type": "application/json",
                # API 密钥
                # "Authorization": "Bearer YOUR_API_KEY"
            },
            "json_args": {
                "model": "neural-chat-7b-v3-1",  # 指定使用的模型
            },
            # 如果有其他需要传递的参数，可以在这里添加
        },
        
        {
            "config_name": "tongyi_chat",
            "model_type": "dashscope_chat", "api_key": API_KEY,
            "model_name": "qwen-turbo"
        },
        {
            "config_name": "tongyi_image",
            "model_type": "dashscope_image_synthesis",
            "api_key": API_KEY,
            "model_name": "wanx-v1"
        }
    ]
)


consulter_prompt = '''
你是我司的着装顾问，你的职责是为顾客提出针对性的着装建议
host给出了顾客的要求，你的回复模板如下：
---
[穿搭建议]
    上衣：{给出一种上衣建议}
    裤子：{给出一种裤子建议}
    鞋子：{给出一种鞋子建议}
    配件：{给出配件建议}
---
为了避免歧义，应当每个部分有且仅有一种风格的推荐（如上衣：不能同时推荐白色T恤和其他颜色的上衣）。
请严格按照上面的模板给出你的建议。当你的建议没有按照模板回答，或是存在推荐不明确的问题时，PM会回复no，并给出相应的说明，你需要按照他给出的提示修改建议
'''

painters_prompt = '''
绘制人物画像
'''

host_prompt = '''
我们是一家为顾客提供穿衣方案的公司，需要根据需求为客户提供今日穿搭建议，以下是一些需要的信息：
1. 今天本地的天气：{}
2. 用户具体需求：{}
{}
'''
# counselor = DialogAgent(
#     name="Consulter",
#     sys_prompt=consulter_prompt,
#     model_config_name="neuralchat_config",  # replace by your model config name
#     # model_config_name="tongyi_chat",  
# )

painter = TextToImageAgent(
    name="Painter",
    sys_prompt=consulter_prompt,
    model_config_name="tongyi_image",  # replace by your model config name
)

user = UserAgent(
    name="user",
)

def get_advice(prompt):
    import openai
    openai.api_key = "EMPTY"
    openai.base_url = 'http://192.168.1.180:1611/v1/'
    response = openai.chat.completions.create(
        model="neural-chat-7b-v3-1",
        # model="chatglm2",
        messages=[
            {"role": "system", "content": "you are a counselor, you need to provide dressing advice for the customer"},
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message

def download_img_pil(index, img_url):
    # print(img_url)
    r = requests.get(img_url, stream=True)
    if r.status_code == 200:
        img = Image.open(io.BytesIO(r.content))
        return (index, img)
    else:
        gr.Error("图片下载失败!")
        return

def download_images(img_urls,batch_size):
    imgs_pil = [None] * batch_size
    # 下载单张图片
    if batch_size == 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            to_do = []
            future = executor.submit(download_img_pil, 1, img_urls)
            to_do.append(future)
            for future in concurrent.futures.as_completed(to_do):
                ret = future.result()
                # worker_results.append(ret)
                index, img_pil = ret
                imgs_pil[index-1] = img_pil 
        return img_pil
    
    else: # 下载多张图片放入gallert中
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            to_do = []
            for i, url in enumerate(img_urls):
                future = executor.submit(download_img_pil, i, url)
                to_do.append(future)

            for future in concurrent.futures.as_completed(to_do):
                ret = future.result()
                # worker_results.append(ret)
                index, img_pil = ret
                imgs_pil[index] = img_pil  # 按顺序排列url，后续下载关联的图片或者svg需要使用
        return imgs_pil

def dress_fn(user_requirement,actors):
    gr.Markdown("请简要描述你的特征及场景：" + user_requirement)
    hint = Msg(
        name="Host",
        content=host_prompt.format(weather, user_requirement,consulter_prompt)  # user 描述示例 26岁男性，体型偏矮微胖，大腿稍粗，前脚略宽；今天去户外运动
    )
    actors = [painter, user]
    with msghub(actors, announcement=hint):
        pass
    new_msg = Msg(name='', content="no")
    advices = []
    # for consulter in [consulter1, consulter2, consulter3]:
    msg = get_advice(hint.content)
    advice = msg.content     
    print("advice", advice)
    return advice

def generate_img(require,output):
    if len(require) == 0:
        raise gr.Error("人物特征不能为空")
        return

    tempt_text = require + output
    new_msg = Msg(name='', content=tempt_text)
    img_res = painter(new_msg)
    img_data = download_images(img_res.url[0], len(img_res.url))
    return img_data


with gr.Blocks(css='style.css',theme=gr.themes.Soft()) as demo:
    with gr.Row():
        with gr.Column(scale=1):
            require = gr.Textbox(label="请简要描述你的特征及场景：", value="30岁男性，170cm，体重60kg，今天去户外运动")
            greet_btn = gr.Button("生成穿搭建议")
        # with gr.Column(scale=3):
            output = gr.Textbox(label="穿搭建议")
        with gr.Column():
            # result = gr.HTML(label='preview', show_label=True, elem_classes='preview_html')
            # result_image = gr.Gallery(
            #    label='preview', show_label=True, elem_classes="preview_imgs", preview=True, interactive=False)
            output_image = gr.Image()
            btn = gr.Button(value="生成穿搭画像", elem_classes='btn_gen')
            gr.Markdown("♨️ 图片较大，加载耗时，稍加等待~")
            # gr.Markdown("📌 鼠标右键保存到本地，或者在新标签页打开大图~")
    greet_btn.click(fn=dress_fn, inputs=require, outputs=output, api_name="dress_fn")
    btn.click(generate_img, inputs=[require,output],outputs=output_image)
    # new_msg = Msg(name='', content=output.value)
    # img_res = painter1(new_msg)
    # print("image", img_res)
    # gr.Image(value=img_res.url[0])

if __name__ == "__main__":
    demo.launch(share=True)

