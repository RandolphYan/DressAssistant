# 概述

- 目标：依托intel extension for transformers及neuralchat、agentscope, 实现基于本地化大语言模型（LLM）的穿搭推荐助手，旨在综合实时天气、场景等外部因素及用户偏好，为用户提供个性化的穿搭推荐及效果展示。

- 核心功能：
  1. 个性化穿搭推荐：综合各类因素，利用大模型能力生成个性化的穿搭建议。
  2. 效果图展示：生成实际效果图，直观展示推荐的穿搭方案。

- 目标用户：穿搭困难症患者及追逐潮流的时尚范儿

# 部署

注：本项目模型服务端和业务层分离，用不同的python环境

## 1. 模型服务端部署

1. 使用conda新建python=3.10.14环境

   ```sh
   conda create -n itrex python=3.10.14
   conda activate itrex
   ```

2. 激活环境，并直接使用pip安装intel-extension-for-transformers=1.4.1

   ```sh
   pip install intel-extension-for-transformers==1.4.1
   ```

3. 使用git从huggingface下载模型

   ```sh
   git lfs install
   git clone https://huggingface.co/Intel/neural-chat-7b-v3-1
   ```

4. 配置neural-chat-server（详见neuralchat.yaml）

5. 使用neural-chat-server启动neuralchat模型服务

   ```sh
   neuralchat_server start --config_file neuralchat.yaml
   ```

## 2. 前端和业务层

本部分依赖agentscope完成

1. 首先新创建python环境

   ```sh
   conda create -n agentscope python=3.10
   conda activate agentscope
   ```

2. 进入项目目录，以源码模式安装

   ```python
   pip install -e .

3. 从阿里云dashboard获取api-key, 命名为DASHSCOPE_API_KEY配置到当前环境

4. 启动服务

   ```sh
   python app.py
   ```