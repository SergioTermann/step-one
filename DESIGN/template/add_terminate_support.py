# -*- coding: utf-8 -*-
"""
为所有模板添加终止功能的辅助脚本
"""
import os
import glob
import re

# 终止服务器代码片段
TERMINATE_CODE = """
# 启动终止服务器
    parser = argparse.ArgumentParser(description='临时解析器获取终止端口')
    parser.add_argument('--terminate-port', type=int, default=9999, help='终止服务器端口')
    args, _ = parser.parse_known_args()
    print(f"终止服务器端口: {args.terminate_port}")
"""

def add_terminate_support_to_file(file_path):
    """向指定文件添加终止支持"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经添加了终止支持
    if "add_terminate_support" in content:
        print(f"文件 {file_path} 已包含终止支持，跳过")
        return
    
    # 查找 if __name__ == "__main__": 后的 main() 调用
    main_pattern = r'if\s+__name__\s*==\s*["\']__main__["\']\s*:(.*?)(\s+main\(\))'
    match = re.search(main_pattern, content, re.DOTALL)
    
    if match:
        # 在main()调用前插入终止服务器代码
        new_content = content.replace(match.group(0), 
                                     f'if __name__ == "__main__":{match.group(1)}{TERMINATE_CODE}{match.group(2)}')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"已向 {file_path} 添加终止支持")
    else:
        print(f"无法在 {file_path} 中找到main()调用，跳过")

def process_all_templates():
    """处理所有模板文件"""
    template_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取所有Python文件
    python_files = []
    for root, _, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.py') and file != 'terminate_server.py' and file != 'add_terminate_support.py':
                python_files.append(os.path.join(root, file))
    
    # 为每个文件添加终止支持
    for file_path in python_files:
        add_terminate_support_to_file(file_path)

if __name__ == "__main__":
    process_all_templates()