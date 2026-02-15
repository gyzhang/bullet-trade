我的 conda 虚拟环境是bullet-trade，我需要在该环境中运行 bullet-trade：
```bash
conda activate bullet-trade
```
切记，我的虚拟环境已经安装好了的，不要自作主张安装环境依赖等操作，我只需要在该环境中运行 bullet-trade 即可。

我的 git 操作参考：
- git push origin kevin-horse - 推送到我的 fork
- git fetch upstream - 从原始项目获取更新
- git merge upstream/main - 合并原始项目的更新

向 github 推送代码遇到网络不通时，请使用如下脚本使用我启动的 VPN 代理：
```bash
export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897 all_proxy=socks5://127.0.0.1:7897
```