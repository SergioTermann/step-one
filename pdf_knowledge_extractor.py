#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import fitz  # PyMuPDF
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFKnowledgeExtractor:
    """PDF知识提取器 - 从PDF文档中提取结构化知识"""
    
    def __init__(self):
        """初始化PDF知识提取器"""
        # 确保NLTK资源可用
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("下载NLTK punkt资源...")
            nltk.download('punkt', quiet=True)
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("下载NLTK stopwords资源...")
            nltk.download('stopwords', quiet=True)
        
        # 加载spaCy模型
        try:
            self.nlp = spacy.load("zh_core_web_sm")
            logger.info("已加载中文NLP模型")
        except:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("已加载英文NLP模型")
            except:
                logger.warning("无法加载NLP模型，将使用基础文本处理")
                self.nlp = None
        
        # 停用词
        self.stop_words = set(stopwords.words('english'))
        try:
            # 添加中文停用词
            with open('chinese_stopwords.txt', 'r', encoding='utf-8') as f:
                chinese_stopwords = set([line.strip() for line in f])
                self.stop_words.update(chinese_stopwords)
        except:
            logger.warning("未找到中文停用词文件，仅使用英文停用词")
    
    def extract_from_pdf(self, pdf_path, min_knowledge_length=10, max_knowledge_length=500):
        """从PDF文件中提取知识
        
        Args:
            pdf_path: PDF文件路径
            min_knowledge_length: 最小知识长度（字符数）
            max_knowledge_length: 最大知识长度（字符数）
            
        Returns:
            dict: 包含提取的知识内容
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return {"error": "文件不存在", "knowledge": []}
        
        try:
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            
            # 提取元数据
            metadata = {
                "title": doc.metadata.get("title", os.path.basename(pdf_path)),
                "author": doc.metadata.get("author", "未知"),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "page_count": len(doc),
                "creation_date": doc.metadata.get("creationDate", ""),
            }
            
            # 提取文本内容
            full_text = ""
            toc = doc.get_toc()
            
            # 提取目录结构
            toc_structure = []
            for level, title, page in toc:
                toc_structure.append({
                    "level": level,
                    "title": title,
                    "page": page
                })
            
            # 提取每页文本
            pages_text = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                pages_text.append(text)
                full_text += text + "\n\n"
            
            # 提取知识点
            knowledge_items = self._extract_knowledge_points(full_text, min_knowledge_length, max_knowledge_length)
            
            # 提取图表信息
            charts_info = self._extract_charts_info(doc)
            
            # 提取关键概念
            key_concepts = self._extract_key_concepts(full_text)
            
            # 构建结果
            result = {
                "metadata": metadata,
                "toc": toc_structure,
                "knowledge_points": knowledge_items,
                "key_concepts": key_concepts,
                "charts_info": charts_info,
                "pages_count": len(doc)
            }
            
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"处理PDF时出错: {str(e)}")
            return {"error": str(e), "knowledge": []}
    
    def _extract_knowledge_points(self, text, min_length=10, max_length=500):
        """从文本中提取知识点
        
        使用NLP技术识别重要句子和段落作为知识点
        """
        knowledge_points = []
        
        # 分割成句子
        sentences = sent_tokenize(text)
        
        # 过滤太短的句子
        filtered_sentences = [s for s in sentences if len(s) >= min_length and len(s) <= max_length]
        
        if not filtered_sentences:
            return knowledge_points
        
        # 使用TF-IDF找出重要句子
        vectorizer = TfidfVectorizer(stop_words=list(self.stop_words), max_features=1000)
        try:
            tfidf_matrix = vectorizer.fit_transform(filtered_sentences)
            
            # 计算每个句子的重要性分数
            importance_scores = np.sum(tfidf_matrix.toarray(), axis=1)
            
            # 选择重要性分数最高的句子
            threshold = np.mean(importance_scores) + 0.5 * np.std(importance_scores)
            
            for i, score in enumerate(importance_scores):
                if score > threshold:
                    # 清理句子
                    sentence = filtered_sentences[i].strip()
                    sentence = re.sub(r'\s+', ' ', sentence)
                    
                    # 检查是否包含有意义的内容
                    if self._is_meaningful(sentence):
                        knowledge_points.append({
                            "content": sentence,
                            "importance": float(score),
                            "type": self._classify_knowledge_type(sentence)
                        })
        
        except Exception as e:
            logger.warning(f"TF-IDF处理失败: {str(e)}")
            # 备选方案：基于长度和关键词的简单提取
            for sentence in filtered_sentences:
                if len(sentence) >= 30 and self._is_meaningful(sentence):
                    knowledge_points.append({
                        "content": sentence.strip(),
                        "importance": 1.0,
                        "type": self._classify_knowledge_type(sentence)
                    })
        
        # 按重要性排序
        knowledge_points.sort(key=lambda x: x["importance"], reverse=True)
        
        # 限制返回的知识点数量
        return knowledge_points[:50]
    
    def _is_meaningful(self, text):
        """判断文本是否包含有意义的内容"""
        # 过滤掉只包含数字、符号的文本
        if re.match(r'^[\d\s\p{P}]+$', text, re.UNICODE):
            return False
            
        # 检查是否包含足够的非停用词
        words = text.split()
        content_words = [w for w in words if w.lower() not in self.stop_words]
        
        return len(content_words) >= 3
    
    def _classify_knowledge_type(self, text):
        """分类知识类型"""
        # 基于关键词的简单分类
        if re.search(r'定义|是指|指的是|称为|叫做|概念', text):
            return "定义"
        elif re.search(r'例如|比如|案例|实例|举例', text):
            return "示例"
        elif re.search(r'步骤|方法|怎么|如何|流程|过程', text):
            return "方法"
        elif re.search(r'原因|因为|所以|导致|引起', text):
            return "原因"
        elif re.search(r'特点|特征|特性|性质|表现', text):
            return "特征"
        else:
            return "信息"
    
    def _extract_charts_info(self, doc):
        """提取文档中的图表信息"""
        charts_info = []
        
        for page_num, page in enumerate(doc):
            # 提取图像
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        charts_info.append({
                            "type": "image",
                            "page": page_num + 1,
                            "index": img_index,
                            "size": f"{base_image['width']}x{base_image['height']}",
                        })
                except Exception as e:
                    logger.warning(f"提取图像失败: {str(e)}")
            
            # 尝试识别表格
            tables = self._detect_tables(page)
            for table_index, table in enumerate(tables):
                charts_info.append({
                    "type": "table",
                    "page": page_num + 1,
                    "index": table_index,
                    "rows": table.get("rows", 0),
                    "columns": table.get("columns", 0)
                })
        
        return charts_info
    
    def _detect_tables(self, page):
        """检测页面中的表格
        
        简单的表格检测，基于线条和文本布局
        """
        tables = []
        
        # 获取页面上的矩形和线条
        rect_lines = page.get_drawings()
        if not rect_lines:
            return tables
            
        # 简单的表格检测逻辑
        horizontal_lines = []
        vertical_lines = []
        
        for item in rect_lines:
            if item["type"] == "l":  # 线条
                p1, p2 = item["rect"][:2], item["rect"][2:]
                if abs(p1[0] - p2[0]) < 3:  # 垂直线
                    vertical_lines.append((min(p1[1], p2[1]), max(p1[1], p2[1]), p1[0]))
                elif abs(p1[1] - p2[1]) < 3:  # 水平线
                    horizontal_lines.append((min(p1[0], p2[0]), max(p1[0], p2[0]), p1[1]))
        
        # 如果有足够的水平和垂直线，可能是表格
        if len(horizontal_lines) >= 3 and len(vertical_lines) >= 3:
            # 估计行数和列数
            rows = len(horizontal_lines) - 1
            cols = len(vertical_lines) - 1
            
            if rows > 0 and cols > 0:
                tables.append({
                    "rows": rows,
                    "columns": cols
                })
        
        return tables
    
    def _extract_key_concepts(self, text):
        """提取关键概念"""
        key_concepts = []
        
        if self.nlp:
            # 使用spaCy进行命名实体识别
            doc = self.nlp(text[:100000])  # 限制处理文本长度
            
            # 收集命名实体
            entities = defaultdict(int)
            for ent in doc.ents:
                if len(ent.text) > 1:  # 过滤单字实体
                    entities[ent.text.strip()] += 1
            
            # 按出现频率排序
            sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)
            
            # 转换为结果格式
            for entity, count in sorted_entities[:30]:  # 限制返回前30个概念
                key_concepts.append({
                    "term": entity,
                    "frequency": count
                })
        else:
            # 备选方案：基于词频的简单提取
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq = defaultdict(int)
            
            for word in words:
                if word not in self.stop_words and len(word) > 1:
                    word_freq[word] += 1
            
            # 按频率排序
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            
            # 转换为结果格式
            for word, count in sorted_words[:30]:
                key_concepts.append({
                    "term": word,
                    "frequency": count
                })
        
        return key_concepts
    
    def save_knowledge_to_json(self, knowledge_data, output_path):
        """将提取的知识保存为JSON文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, ensure_ascii=False, indent=2)
            logger.info(f"知识已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存知识失败: {str(e)}")
            return False


# 测试代码
if __name__ == "__main__":
    extractor = PDFKnowledgeExtractor()
    
    # 测试PDF路径
    pdf_path = input("请输入PDF文件路径: ")
    
    if os.path.exists(pdf_path):
        print(f"正在处理: {pdf_path}")
        knowledge = extractor.extract_from_pdf(pdf_path)
        
        # 保存结果
        output_path = os.path.splitext(pdf_path)[0] + "_knowledge.json"
        extractor.save_knowledge_to_json(knowledge, output_path)
        
        # 显示部分结果
        print("\n提取的知识点:")
        for i, item in enumerate(knowledge.get("knowledge_points", [])[:5]):
            print(f"{i+1}. [{item['type']}] {item['content'][:100]}...")
        
        print(f"\n共提取 {len(knowledge.get('knowledge_points', []))} 个知识点")
        print(f"结果已保存到: {output_path}")
    else:
        print("文件不存在!")