# SmartCalligraphy
墨韵童习-AI辅助书法教学系统：本项目由AI辅助开发。



**特别声明 (Special Notice)**

本项目仅供学习和研究使用。**禁止任何形式的商业用途**（包括但不限于将其用于商业软件、SaaS 服务或进行二次分发销售）。

如需商业授权，请联系作者。

This project is for educational and research purposes only. **Commercial use is strictly prohibited.**



#### 运行环境：Win11/python3.12

##### 安装项目依赖

```shell
pip install -r requirements.txt --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple
```

关键依赖包（自动安装）：
lazyllm：工作流与 RAG 编排
gradio：前端界面启动
chromadb：向量知识库存储

##### 配置文件初始化

确认 config.yaml 提示词配置文件在项目根目录，更新配置文件中以下内容：

```yaml
model:
  source: "XXX"             # 调用大模型的API类型
  base_url: "XXX"           # 调用大模型API的URL
  siliconflow_key: "XXX"    # 硅基流动的api_key用于免费bge-m3向量化
  api_key: "XXX"            # 调用大模型API的key
  vision_model: "XXX"       # 视觉大模型 (用于书法作品分析)
  text_model: "XXX"         # 文本模型 (用于对话)
  embed_model: "XXX"        # 文本嵌入模型 (用于向量化)
  image_model: "XXX"        # 图像生成模型 (用于意象图生成)
```

##### 启动平台

```shell
python app.py
```

启动成功后，控制台输出：

* Running on local URL:  http://0.0.0.0:7860

在浏览器上输入地址：http://localhost:7860/，打开即可使用。

