#!/usr/bin/env python3
"""
音乐AI标签生成系统 - 修复版
"""

import os
import sys
import json
import redis
import logging
import pymysql
import requests
import time
import signal
from typing import List, Optional, Dict, Any
from datetime import datetime
import subprocess
from requests.exceptions import ConnectionError, Timeout

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_labeling_fixed.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 优雅退出处理
stop_flag = False

def signal_handler(sig, frame):
    global stop_flag
    logger.info("收到停止信号，正在优雅退出...")
    stop_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class MusicLabelingSystemFixed:
    def __init__(self):
        # 数据库配置
        self.db_config = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'root',
            'password': 'wwq_2021',
            'database': 'play',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        # Redis配置
        self.redis_config = {
            'host': '127.0.0.1',
            'port': 6379,
            'db': 0,
            'decode_responses': True
        }
        
        # Ollama配置
        self.ollama_url = "http://localhost:11434"
        self.model_name = "qwen3.5:27b"  # 修改为正确的模型名称
        
        # Redis键名
        self.redis_processed_key = 'music:processed:songs'
        self.redis_ai_labeled_key = 'music:ai_labeled:songs'
        self.redis_failed_key = 'music:failed:songs'
        self.redis_retry_key = 'music:retry:queue'
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 5
        
        # 初始化连接
        self.init_connections()
        self.check_ollama()
    
    def init_connections(self):
        """初始化数据库和Redis连接"""
        try:
            # MySQL连接
            self.db_conn = pymysql.connect(**self.db_config)
            self.db_cursor = self.db_conn.cursor()
            logger.info("MySQL连接成功")
            
            # Redis连接
            self.redis_client = redis.Redis(**self.redis_config)
            self.redis_client.ping()
            logger.info("Redis连接成功")
            
        except Exception as e:
            logger.error(f"连接初始化失败: {e}")
            raise
    
    def check_ollama(self):
        """检查Ollama服务状态和模型"""
        try:
            # 检查Ollama服务
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models]
                logger.info(f"Ollama服务正常，可用模型: {model_names}")
                
                # 检查所需模型是否存在
                if self.model_name in model_names:
                    logger.info(f"模型 {self.model_name} 可用")
                else:
                    logger.warning(f"模型 {self.model_name} 未找到，可用模型: {model_names}")
                    # 尝试使用第一个可用模型
                    if model_names:
                        self.model_name = model_names[0]
                        logger.info(f"自动切换到模型: {self.model_name}")
                    else:
                        logger.error("没有可用的模型")
                        self.start_ollama_model()
            else:
                logger.error(f"Ollama API响应异常: {response.status_code}")
                self.start_ollama_service()
                
        except ConnectionError:
            logger.error("无法连接到Ollama服务，正在尝试启动...")
            self.start_ollama_service()
        except Exception as e:
            logger.error(f"检查Ollama失败: {e}")
            self.start_ollama_service()
    
    def start_ollama_service(self):
        """尝试启动Ollama服务"""
        try:
            logger.info("尝试启动Ollama服务...")
            
            # 检查是否已安装ollama
            result = subprocess.run(['which', 'ollama'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                # 启动ollama服务（后台运行）
                subprocess.Popen(['ollama', 'serve'])
                logger.info("Ollama服务已启动")
                time.sleep(10)  # 等待服务启动
                
                # 加载模型
                self.start_ollama_model()
            else:
                logger.error("未找到Ollama，请先安装: https://ollama.com")
                
        except Exception as e:
            logger.error(f"启动Ollama服务失败: {e}")
    
    def start_ollama_model(self):
        """启动/拉取模型"""
        try:
            logger.info(f"尝试加载模型: {self.model_name}")
            
            # 尝试拉取模型
            subprocess.run(['ollama', 'pull', self.model_name], 
                          capture_output=True, text=True)
            
            # 运行模型
            subprocess.Popen(['ollama', 'run', self.model_name])
            logger.info(f"模型 {self.model_name} 已启动")
            time.sleep(15)  # 给模型加载时间
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            # 尝试使用较小的模型
            self.model_name = "qwen2.5:7b"
            logger.info(f"尝试使用较小的模型: {self.model_name}")
            self.start_ollama_model()
    
    def close_connections(self):
        """关闭所有连接"""
        try:
            if hasattr(self, 'db_cursor'):
                self.db_cursor.close()
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
            if hasattr(self, 'redis_client'):
                self.redis_client.close()
            logger.info("所有连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接时出错: {e}")
    
    def generate_labels_with_ai(self, song_info: Dict, retry_count: int = 0) -> Optional[str]:
        """调用Ollama生成标签（带重试机制）"""
        if retry_count >= self.max_retries:
            logger.error(f"达到最大重试次数，跳过歌曲 (ID: {song_info.get('id')})")
            return None
        
        try:
            prompt = self.generate_prompt(song_info)
            
            # 使用更稳定的API调用方式
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 100
                }
            }
            
            logger.debug(f"调用AI模型: {self.model_name}")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120  # 增加超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                labels = result.get('response', '').strip()
                
                # 清理输出
                labels = self.clean_labels(labels)
                logger.info(f"AI生成成功 (ID: {song_info.get('id')}): {labels}")
                return labels
            else:
                logger.warning(f"AI调用失败，状态码: {response.status_code}")
                if retry_count < self.max_retries - 1:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    return self.generate_labels_with_ai(song_info, retry_count + 1)
                else:
                    logger.error(f"重试失败 (ID: {song_info.get('id')})")
                    return None
                    
        except Timeout:
            logger.warning(f"AI调用超时 (ID: {song_info.get('id')})")
            if retry_count < self.max_retries - 1:
                logger.info(f"等待 {self.retry_delay} 秒后重试...")
                time.sleep(self.retry_delay)
                return self.generate_labels_with_ai(song_info, retry_count + 1)
        except ConnectionError:
            logger.error(f"无法连接到Ollama服务 (ID: {song_info.get('id')})")
            # 尝试重启服务
            if retry_count == 0:
                self.check_ollama()
                time.sleep(10)
                return self.generate_labels_with_ai(song_info, retry_count + 1)
        except Exception as e:
            logger.error(f"AI生成标签异常 (ID: {song_info.get('id')}): {e}")
            if retry_count < self.max_retries - 1:
                time.sleep(self.retry_delay)
                return self.generate_labels_with_ai(song_info, retry_count + 1)
        
        return None
    
    def generate_prompt(self, song_info: Dict) -> str:
        """生成优化的AI提示词"""
        song_name = song_info.get('song_name', '未知').strip()
        author_name = song_info.get('author_name', '未知').strip()
        album_name = song_info.get('album_name', '未知').strip()
        lyrics = song_info.get('lyrics', '')
        
        # 简化提示词，提高成功率
        prompt = f"""请为以下歌曲生成3-5个音乐标签，用逗号分隔：

歌曲：{song_name}
歌手：{author_name}
专辑：{album_name}
歌词片段：{lyrics[:300] if lyrics else "无歌词"}

标签要求：
1. 只输出标签，不要解释
2. 用中文逗号分隔
3. 3-5个中文标签
4. 参考：流行、摇滚、民谣、伤感、快乐、爱情、励志、治愈

标签："""
        
        return prompt
    
    def clean_labels(self, labels: str) -> str:
        """清理和验证标签"""
        if not labels:
            return ""
        
        # 移除多余的空格和换行
        labels = labels.strip()
        
        # 替换中文标点
        labels = labels.replace('，', ',').replace('、', ',').replace('；', ',')
        labels = labels.replace('。', '').replace('！', '').replace('？', '')
        
        # 分割并清理标签
        label_list = []
        for label in labels.split(','):
            label = label.strip()
            if label and len(label) <= 10:  # 标签长度限制
                label_list.append(label)
        
        # 去重
        unique_labels = []
        for label in label_list:
            if label not in unique_labels:
                unique_labels.append(label)
        
        # 限制数量
        if len(unique_labels) > 5:
            unique_labels = unique_labels[:5]
        elif len(unique_labels) < 3 and unique_labels:
            # 如果标签太少，添加默认标签
            default_tags = ["流行", "情感"]
            for tag in default_tags:
                if tag not in unique_labels and len(unique_labels) < 5:
                    unique_labels.append(tag)
        
        return ','.join(unique_labels)
    
    def get_unprocessed_songs(self, batch_size: int = 10) -> List[Dict]:
        """
        获取需要处理的歌曲（优化查询）
        """
        try:
            # 从Redis获取已处理的ID
            processed_ids = self.redis_client.smembers(self.redis_processed_key)
            processed_ids_list = list(processed_ids) if processed_ids else []
            
            # 构建查询条件
            query = """
            SELECT id, song_name, author_name, album_name, lyrics, label
            FROM music
            WHERE (
                label IS NULL 
                OR label = '' 
                OR label NOT LIKE '%,%,%'  -- 至少有两个逗号（3个标签）
            )
            AND lyrics IS NOT NULL 
            AND lyrics != ''
            AND LENGTH(lyrics) > 20
            ORDER BY id ASC
            LIMIT %s
            """
            
            self.db_cursor.execute(query, (batch_size,))
            songs = self.db_cursor.fetchall()
            
            # 过滤已处理的歌曲
            filtered_songs = []
            for song in songs:
                if str(song['id']) not in processed_ids_list:
                    filtered_songs.append(song)
                else:
                    logger.debug(f"跳过已处理歌曲 (ID: {song['id']})")
            
            logger.info(f"获取到 {len(filtered_songs)} 首待处理歌曲（过滤后）")
            return filtered_songs[:batch_size]  # 确保不超过批次大小
            
        except Exception as e:
            logger.error(f"获取未处理歌曲失败: {e}")
            return []
    
    def process_single_song(self, song: Dict) -> bool:
        """处理单首歌曲"""
        global stop_flag
        if stop_flag:
            return False
        
        song_id = song['id']
        
        logger.info(f"处理歌曲 (ID: {song_id}): {song.get('song_name', '未知')}")
        
        try:
            # 调用AI生成标签
            labels = self.generate_labels_with_ai(song)
            
            if not labels:
                self.mark_as_failed(song_id, "AI生成标签失败")
                return False
            
            # 更新数据库
            if self.update_song_labels(song_id, labels):
                # 记录到Redis
                self.mark_as_processed(song_id)
                self.mark_as_ai_labeled(song_id, labels)
                logger.info(f"✅ 处理成功 (ID: {song_id}): {labels}")
                return True
            else:
                self.mark_as_failed(song_id, "数据库更新失败")
                return False
                
        except Exception as e:
            logger.error(f"处理歌曲失败 (ID: {song_id}): {e}")
            self.mark_as_failed(song_id, str(e))
            return False
    
    def update_song_labels(self, song_id: int, labels: str) -> bool:
        """更新数据库中的标签"""
        try:
            update_query = """
            UPDATE music 
            SET label = %s, update_time = NOW()
            WHERE id = %s
            """
            
            self.db_cursor.execute(update_query, (labels, song_id))
            self.db_conn.commit()
            
            return True
            
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"更新数据库失败 (ID: {song_id}): {e}")
            return False
    
    def mark_as_processed(self, song_id: int):
        """标记歌曲为已处理"""
        self.redis_client.sadd(self.redis_processed_key, str(song_id))
    
    def mark_as_ai_labeled(self, song_id: int, labels: str):
        """记录AI生成的标签"""
        data = {
            'song_id': song_id,
            'labels': labels,
            'timestamp': datetime.now().isoformat(),
            'model': self.model_name
        }
        self.redis_client.hset(self.redis_ai_labeled_key, str(song_id), json.dumps(data))
    
    def mark_as_failed(self, song_id: int, error: str):
        """记录处理失败的歌曲"""
        data = {
            'song_id': song_id,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'retry_count': 0
        }
        self.redis_client.hset(self.redis_failed_key, str(song_id), json.dumps(data))
    
    def process_batch(self, batch_size: int = 5, delay: float = 2.0):
        """批量处理歌曲"""
        logger.info(f"开始批量处理，批次大小: {batch_size}")
        
        processed_count = 0
        failed_count = 0
        
        while not stop_flag:
            try:
                # 获取待处理歌曲
                songs = self.get_unprocessed_songs(batch_size)
                
                if not songs:
                    logger.info("没有更多待处理歌曲")
                    break
                
                # 处理批次
                batch_success = 0
                for song in songs:
                    if stop_flag:
                        break
                    
                    if self.process_single_song(song):
                        batch_success += 1
                        processed_count += 1
                    else:
                        failed_count += 1
                    
                    # 添加延迟避免请求过快
                    if not stop_flag:
                        time.sleep(delay)
                
                logger.info(f"批次处理完成: 成功 {batch_success}/{len(songs)}")
                logger.info(f"累计统计: 成功 {processed_count}, 失败 {failed_count}")
                
                # 如果批次处理数量少，可能处理完毕
                if len(songs) < batch_size:
                    logger.info("批次数量不足，可能已处理完毕")
                    break
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"批次处理异常: {e}")
                if not stop_flag:
                    time.sleep(5)
    
    def get_statistics(self) -> Dict:
        """获取处理统计"""
        try:
            stats = {
                'total_processed': self.redis_client.scard(self.redis_processed_key),
                'total_ai_labeled': self.redis_client.hlen(self.redis_ai_labeled_key),
                'total_failed': self.redis_client.hlen(self.redis_failed_key)
            }
            
            # 获取数据库总数
            self.db_cursor.execute("SELECT COUNT(*) as total FROM music")
            total_songs = self.db_cursor.fetchone()['total']
            stats['total_songs'] = total_songs
            
            # 获取已标签的歌曲数量
            self.db_cursor.execute("""
                SELECT COUNT(*) as labeled_count 
                FROM music 
                WHERE label IS NOT NULL 
                AND label != '' 
                AND label LIKE '%,%'
            """)
            labeled_count = self.db_cursor.fetchone()['labeled_count']
            stats['total_labeled'] = labeled_count
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {}
    
    def run(self, continuous: bool = False, interval: int = 300):
        """运行标签生成系统"""
        try:
            logger.info("=" * 50)
            logger.info("启动音乐标签生成系统 (修复版)")
            logger.info(f"使用模型: {self.model_name}")
            logger.info("=" * 50)
            
            # 显示统计信息
            stats = self.get_statistics()
            logger.info(f"系统统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
            
            if continuous:
                logger.info(f"持续运行模式，检查间隔: {interval}秒")
                while not stop_flag:
                    self.process_batch(batch_size=5, delay=2.0)
                    if not stop_flag:
                        logger.info(f"等待 {interval} 秒后进行下一轮处理...")
                        time.sleep(interval)
            else:
                logger.info("单次运行模式")
                self.process_batch(batch_size=10, delay=1.5)
                
        except KeyboardInterrupt:
            logger.info("系统被用户中断")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
        finally:
            # 最终统计
            stats = self.get_statistics()
            logger.info("=" * 50)
            logger.info("处理完成")
            logger.info(f"最终统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
            logger.info("=" * 50)
            
            self.close_connections()

def main():
    """主函数"""
    # 添加详细的启动信息
    logger.info("正在初始化系统...")
    
    try:
        system = MusicLabelingSystemFixed()
        
        # 运行模式选择
        # 单次运行：continuous=False
        # 持续运行：continuous=True（会定期检查新歌曲）
        system.run(continuous=False, interval=300)
        
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        logger.error("请检查：")
        logger.error("1. MySQL服务是否运行")
        logger.error("2. Redis服务是否运行")
        logger.error("3. Ollama服务是否运行")
        logger.error("4. 模型是否已下载 (ollama pull qwen3.5:27b)")

if __name__ == "__main__":
    main()