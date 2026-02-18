from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import os

# 尝试导入 agentscope
agentscope_available = False
try:
    from agentscope.model import DashScopeChatModel
    from agentscope.message import Msg as ASMsg
    from agentscope import init
    # 初始化 agentscope
    init()
    agentscope_available = True
except ImportError as e:
    print(f"导入 agentscope 失败: {e}")
except Exception as e:
    print(f"导入 agentscope 时发生其他错误: {e}")

# 定义基础 AgentBase 类
class AgentBase:
    def __init__(self, name, model_config_name, use_memory=True, **kwargs):
        self.name = name
        self.model_config_name = model_config_name
        self.use_memory = use_memory
        self.model = None
        
        # 如果 agentscope 可用，初始化模型
        if agentscope_available:
            try:
                # 从环境变量中读取 API 密钥
                api_key = os.getenv('DASHSCOPE_API_KEY')
                if not api_key:
                    print("未找到 DASHSCOPE_API_KEY 环境变量")
                    return
                
                # 使用 DashScopeChatModel 初始化阿里云模型
                self.model = DashScopeChatModel(
                    model_name=model_config_name,
                    api_key=api_key
                )
            except Exception as e:
                print(f"初始化模型失败: {e}")
    
    # 辅助方法：处理异步生成器并返回完整内容
    async def _get_model_response(self, prompt):
        try:
            # 限制提示词长度，避免 API 错误
            max_prompt_length = 2000
            if len(prompt) > max_prompt_length:
                prompt = prompt[:max_prompt_length] + "..."
            
            # 使用消息列表格式调用模型
            messages = [{"role": "user", "content": prompt}]
            result = await self.model(messages)
            
            # 处理返回结果
            full_content = ""
            
            # 检查 result 类型
            if hasattr(result, '__aiter__'):
                # 是异步生成器
                async for chunk in result:
                    if hasattr(chunk, 'content'):
                        # 处理 ChatResponse 对象
                        content = chunk.content
                        if isinstance(content, list):
                            # 如果是列表，将其转换为字符串
                            for item in content:
                                if isinstance(item, dict) and 'text' in item:
                                    full_content += item['text']
                                else:
                                    full_content += str(item)
                        else:
                            # 如果是字符串，直接添加
                            full_content += str(content)
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        content = chunk['content']
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and 'text' in item:
                                    full_content += item['text']
                                else:
                                    full_content += str(item)
                        else:
                            full_content += str(content)
                    elif isinstance(chunk, str):
                        full_content += chunk
                    else:
                        # 其他类型，转换为字符串
                        full_content += str(chunk)
            elif hasattr(result, 'content'):
                # 是带有 content 属性的对象
                content = result.content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            full_content += item['text']
                        else:
                            full_content += str(item)
                else:
                    full_content = str(content)
            elif isinstance(result, dict) and 'content' in result:
                # 是带有 content 键的字典
                content = result['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            full_content += item['text']
                        else:
                            full_content += str(item)
                else:
                    full_content = str(content)
            elif isinstance(result, str):
                # 是字符串
                full_content = result
            else:
                # 其他类型
                full_content = str(result)
            
            # 去除重复内容
            full_content = self._remove_duplicates(full_content)
            
            return full_content
        except Exception as e:
            print(f"模型调用错误: {e}")
            return f"模型调用失败: {str(e)}"
    
    # 辅助方法：去除重复内容
    def _remove_duplicates(self, text):
        """去除文本中的重复内容"""
        if not text:
            return text
        
        # 1. 去除完全重复的行
        lines = text.split('\n')
        seen_lines = set()
        unique_lines = []
        
        for line in lines:
            line = line.strip()
            if line and line not in seen_lines:
                seen_lines.add(line)
                unique_lines.append(line)
        
        # 2. 去除句子级别的重复
        cleaned_text = '\n'.join(unique_lines)
        
        # 3. 去除连续重复的单词
        words = cleaned_text.split()
        if not words:
            return cleaned_text
        
        unique_words = [words[0]]
        for word in words[1:]:
            if word != unique_words[-1]:
                unique_words.append(word)
        
        # 4. 修复常见的重复模式
        cleaned_text = ' '.join(unique_words)
        
        # 5. 修复常见的重复短语
        common_duplicates = [
            '根据根据', '根据您根据您', '分析分析', '市场市场',
            '趋势趋势', '建议建议', '风险风险', '投资投资',
            '策略策略', '板块板块', '个股个股', '指标指标',
            '评估评估', '建议建议', '分析分析', '预测预测',
            '判断判断', '认为认为', '预期预期', '建议建议'
        ]
        
        for duplicate in common_duplicates:
            # 将重复短语替换为单个短语
            single = duplicate[:len(duplicate)//2]
            cleaned_text = cleaned_text.replace(duplicate, single)
        
        # 6. 修复常见的重复前缀模式
        prefix_duplicates = [
            '## 市场趋势分析## 市场趋势分析',
            '## 市场趋势分析 ## 市场趋势分析',
            '#### 市## 市场趋势分析',
            '## 市场趋势分析 - **当前市场所处## 市场趋势分析'
        ]
        
        for pattern in prefix_duplicates:
            replacement = pattern.split('##')[2].strip() if len(pattern.split('##')) > 2 else '市场趋势分析'
            cleaned_text = cleaned_text.replace(pattern, f'## {replacement}')
        
        # 7. 去除多余的空格和换行
        cleaned_text = ' '.join(cleaned_text.split())
        cleaned_text = cleaned_text.replace('\n\n', '\n')
        cleaned_text = cleaned_text.replace('  ', ' ')
        
        return cleaned_text

# 定义 Msg 类
class Msg:
    def __init__(self, name, content, role):
        self.name = name
        self.content = content
        self.role = role


class BaseFinanceAgent(AgentBase, ABC):
    def __init__(
        self,
        name: str,
        model_config_name: str,
        use_memory: bool = True,
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            use_memory=use_memory,
            **kwargs
        )
        self.role = "金融智能体"
        self.description = "基础金融智能体类"
    
    @abstractmethod
    def reply(self, x: Optional[Msg] = None) -> Msg:
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
        }
