# AgentScope 集成指南

## 概述

本项目已集成 AgentScope 框架，用于构建智能投资决策系统。AgentScope 是阿里巴巴开源的多智能体开发框架，支持构建复杂的多智能体协作系统。通过集成智能体，我们的交易策略能够获得更全面的市场分析、更精准的投资建议和更有效的风险管理。

## 安装

### 1. 安装依赖
```bash
conda activate bullet-trade
pip install agentscope
```

### 2. 配置环境变量
复制配置文件模板：
```bash
cp env.agentscope.example .env
```

编辑 `.env` 文件，填入你的 API 密钥：
```bash
# 阿里云 DashScope（推荐）
DASHSCOPE_API_KEY=your_dashscope_key
DASHSCOPE_MODEL=qwen-max

# 或使用 OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
```

## 架构设计

### 智能体角色

1. **数据分析师 (DataAnalystAgent)**
   - 分析市场数据和趋势
   - 解读技术指标和波动率
   - 识别板块轮动和市场情绪
   - 提供详细的市场分析报告

2. **策略顾问 (StrategyAdvisorAgent)**
   - 基于市场分析提供投资策略建议
   - 推荐具体交易标的及理由
   - 设计仓位配置和行业配置方案
   - 提供具体的交易策略指导

3. **风险控制官 (RiskControllerAgent)**
   - 评估投资组合风险
   - 提供风险控制建议
   - 监控风险敞口和回撤
   - 设计风险管理策略

4. **交易执行员 (ExecutorAgent)**
   - 生成交易指令和执行计划
   - 优化交易执行策略
   - 监控执行过程和效果
   - 提供执行报告

5. **投资报告员 (ReporterAgent)**
   - 生成投资报告和总结
   - 分析投资绩效和经验
   - 提供改进建议和优化方向

### 工作流程

```
市场数据 → 数据分析 → 策略建议 → 风险评估 → 交易执行 → 生成报告
```

## 与交易策略整合

### 策略集成示例

```python
from jqdata import *
from bullet_trade.agents import (
    DataAnalystAgent,
    StrategyAdvisorAgent,
    RiskControllerAgent,
    Msg
)

def initialize(context):
    # 初始化智能体
    g.data_analyst = DataAnalystAgent()
    g.strategy_advisor = StrategyAdvisorAgent()
    g.risk_controller = RiskControllerAgent()
    
    # 智能体分析结果缓存
    g.agent_analysis = {}
    
    run_daily(period, time='14:30')

def get_market_analysis(context):
    """获取市场分析结果"""
    # 准备市场数据
    market_data = f"""
    市场数据:
    - 大盘趋势: {check_market_trend(context)}
    - 市场波动率: {get_market_volatility(context, g.stocks)*100:.2f}%
    - 跟踪股票: {', '.join(g.stocks)}
    """
    
    # 使用数据分析师智能体分析市场
    analysis_msg = g.data_analyst.reply(Msg(name="strategy", content=market_data, role="user"))
    
    return analysis_msg.content

def period(context):
    # 每周一进行智能体分析
    if context.current_dt.weekday() == 0:  # 周一
        log.info("=== 智能体市场分析 ===")
        analysis_result = get_market_analysis(context)
        g.agent_analysis['market'] = analysis_result
        log.info(f"智能体分析结果: {analysis_result[:200]}...")
        
        # 使用策略顾问智能体获取策略建议
        strategy_msg = g.strategy_advisor.reply(Msg(name="strategy", content=analysis_result, role="user"))
        g.agent_analysis['strategy'] = strategy_msg.content
        log.info(f"策略建议: {strategy_msg.content[:200]}...")
        
        # 使用风险控制官智能体评估风险
        risk_msg = g.risk_controller.reply(Msg(name="strategy", content=strategy_msg.content, role="user"))
        g.agent_analysis['risk'] = risk_msg.content
        log.info(f"风险评估: {risk_msg.content[:200]}...")
    
    # 从智能体分析结果中提取推荐股票
    recommended_stocks = []
    if 'strategy' in g.agent_analysis:
        # 提取推荐股票的逻辑
        # ...
    
    # 结合智能体推荐和技术分析进行选股和交易
    # ...
```

### 推荐股票提取

我们实现了智能的推荐股票提取逻辑，能够从智能体的分析结果中识别推荐的股票：

```python
# 从智能体分析结果中提取推荐股票
def extract_recommended_stocks(strategy_content, market_content, all_stocks):
    recommended_stocks = []
    import re
    
    # 1. 检查股票代码是否在策略内容中
    for stock in all_stocks:
        if stock in strategy_content:
            recommended_stocks.append(stock)
    
    # 2. 从推荐部分提取股票
    if not recommended_stocks:
        patterns = [
            r'推荐关注的个股.*?([\d\.XSHGXSHE,\s]+)',
            r'推荐个股.*?([\d\.XSHGXSHE,\s]+)',
            r'关注个股.*?([\d\.XSHGXSHE,\s]+)',
            r'建议关注.*?([\d\.XSHGXSHE,\s]+)',
            r'推荐.*?([\d\.XSHGXSHE,\s]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, strategy_content, re.DOTALL)
            for match in matches:
                stock_candidates = re.findall(r'\d+\.\w+', match)
                for candidate in stock_candidates:
                    if candidate in all_stocks and candidate not in recommended_stocks:
                        recommended_stocks.append(candidate)
    
    # 3. 如果仍然没有推荐，基于市场分析选择股票
    if not recommended_stocks and market_content:
        if '牛市' in market_content or '上涨' in market_content:
            # 牛市环境下选择成长股
            growth_stocks = ['300017.XSHE', '300674.XSHE', '300380.XSHE']
            for stock in growth_stocks:
                if stock in all_stocks:
                    recommended_stocks.append(stock)
        elif '熊市' in market_content or '下跌' in market_content:
            # 熊市环境下选择防御股
            defensive_stocks = ['600036.XSHG', '601318.XSHG', '600900.XSHG']
            for stock in defensive_stocks:
                if stock in all_stocks:
                    recommended_stocks.append(stock)
        else:
            # 震荡市选择均衡配置
            balanced_stocks = ['600036.XSHG', '601318.XSHG', '000858.XSHE']
            for stock in balanced_stocks:
                if stock in all_stocks:
                    recommended_stocks.append(stock)
    
    return recommended_stocks
```

## 使用示例

### 示例1: 单个智能体使用
```python
from bullet_trade.agents import DataAnalystAgent, Msg

# 创建智能体
analyst = DataAnalystAgent()

# 分析数据
market_data = "沪深300指数今日收盘于3800点，波动率为30%，市场趋势中性..."
result = analyst.reply(Msg(name="user", content=market_data, role="user"))
print(result.content)
```

### 示例2: 多智能体协作
```python
from bullet_trade.agents import (
    DataAnalystAgent,
    StrategyAdvisorAgent,
    RiskControllerAgent,
    Msg
)

# 创建智能体
analyst = DataAnalystAgent()
advisor = StrategyAdvisorAgent()
risk_controller = RiskControllerAgent()

# 运行分析流程
market_data = "市场概况：沪深300指数..."

# 1. 市场分析
analysis = analyst.reply(Msg(name="user", content=market_data, role="user"))
print("=== 市场分析 ===")
print(analysis.content)

# 2. 策略建议
strategy = advisor.reply(Msg(name="user", content=analysis.content, role="user"))
print("=== 策略建议 ===")
print(strategy.content)

# 3. 风险评估
risk = risk_controller.reply(Msg(name="user", content=strategy.content, role="user"))
print("=== 风险评估 ===")
print(risk.content)
```

## 运行示例

```bash
# 运行完整示例
python examples/agentscope_demo.py

# 运行策略回测（集成了智能体）
bash helloworld4.sh
```

## 自定义智能体

### 创建新的智能体
```python
from bullet_trade.agents.base import BaseFinanceAgent
from bullet_trade.agents import Msg

class MyCustomAgent(BaseFinanceAgent):
    def __init__(self, name: str = "MyAgent", model_config_name: str = "qwen-max", **kwargs):
        super().__init__(name=name, model_config_name=model_config_name, **kwargs)
        self.role = "自定义智能体"
        self.description = "我的自定义智能体"
    
    def reply(self, x: Msg = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供需要分析的信息",
                role="assistant"
            )
        
        # 构建提示词
        prompt = f"""
        作为{self.role}，请分析以下信息：
        {x.content}
        
        请提供详细的分析和建议。
        """
        
        try:
            import asyncio
            
            async def call_model():
                return await self._get_model_response(prompt)
            
            content = asyncio.run(call_model())
            
            return Msg(
                name=self.name,
                content=content,
                role="assistant"
            )
        except Exception as e:
            return Msg(
                name=self.name,
                content=f"模型调用失败: {str(e)}",
                role="assistant"
            )
```

### 注册智能体
```python
# 在 bullet_trade/agents/__init__.py 中添加
from .my_custom_agent import MyCustomAgent

__all__ = [
    # ... 其他智能体
    'MyCustomAgent',
]
```

## 高级功能

### 1. 工具集成
为智能体添加自定义工具：
```python
from agentscope.agents import ReActAgent
from agentscope.model import OpenAIChatModel

def get_stock_price(stock_code: str) -> str:
    """获取股票实时价格"""
    # 实现获取股票价格的逻辑
    return f"{stock_code}: 35.2元"

def get_market_trend() -> str:
    """获取市场趋势"""
    # 实现获取市场趋势的逻辑
    return "市场趋势：中性"

# 创建带工具的智能体
agent = ReActAgent(
    name="StockAgent",
    model=OpenAIChatModel(model="gpt-4o"),
    tools=[get_stock_price, get_market_trend]
)
```

### 2. 记忆管理
```python
# 启用记忆
agent = DataAnalystAgent(
    model_config_name="qwen-max",
    use_memory=True
)

# 清除记忆
agent.clear_memory()
```

### 3. 流式输出
```python
# 启用流式输出
response = agent.model(x, stream=True)
for chunk in response:
    print(chunk.content, end="", flush=True)
```

## 最佳实践

### 1. 模型选择
- **数据分析**：使用温度较高的模型（0.7-0.8），鼓励创造性分析
- **风险控制**：使用温度较低的模型（0.3-0.5），确保严谨性
- **交易执行**：使用温度最低的模型（0.1-0.3），确保准确性

### 2. 提示词工程
- 明确角色定位和分析目标
- 提供具体的分析框架和要求
- 要求结构化输出和明确结论
- 限制响应长度，确保简洁有效

### 3. 错误处理
```python
try:
    result = agent.reply(msg)
except Exception as e:
    print(f"智能体执行失败: {e}")
    # 降级处理或使用默认策略
    result = Msg(name="system", content="智能体暂时不可用，使用默认策略", role="assistant")
```

### 4. 成本控制
- 使用缓存减少重复调用
- 合理设置 max_tokens 和提示词长度
- 选择性价比高的模型
- 批量处理分析请求

### 5. 性能优化
- 异步处理模型调用
- 缓存分析结果
- 限制智能体调用频率（如每周一次）
- 优化响应处理和解析

## 注意事项

1. **API 密钥安全**：不要将 API 密钥提交到代码仓库
2. **成本控制**：监控 API 调用次数和费用
3. **数据隐私**：不要将敏感数据发送到外部 API
4. **模型限制**：注意模型的 token 限制和速率限制
5. **响应质量**：智能体的响应可能存在重复内容，需要进行后处理
6. **回测性能**：智能体调用可能会增加回测时间，建议合理设置调用频率

## 故障排除

### 常见问题

1. **智能体响应重复内容**
   - 原因：模型可能产生重复的思考过程
   - 解决：我们已实现自动去重功能，会自动处理重复内容

2. **智能体调用超时**
   - 原因：模型响应时间过长
   - 解决：增加超时处理，设置合理的超时时间

3. **推荐股票提取失败**
   - 原因：智能体响应格式不符合预期
   - 解决：使用备用推荐逻辑，基于市场趋势选择股票

4. **API 调用失败**
   - 原因：API 密钥无效或速率限制
   - 解决：检查 API 密钥，实现重试机制

## 参考资料

- [AgentScope 官方文档](https://doc.agentscope.io)
- [AgentScope GitHub](https://github.com/agentscope-ai/agentscope)
- [阿里云 DashScope](https://dashscope.aliyun.com)

## 获取帮助

如有问题，请：
1. 查看官方文档
2. 提交 Issue
3. 联系维护团队
