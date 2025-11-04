# -*- coding: utf-8 -*-
import os
import glob
import re

TERMINATOR_CODE = """
try:
    from process_terminator import get_terminator, register_current_process
    process_number = args.name if hasattr(args, 'name') else os.path.basename(__file__).split('.')[0]
    terminator = get_terminator(port=args.terminate_port if hasattr(args, 'terminate_port') else 9999)
    register_current_process(process_number)
    print(f"已启动进程终止HTTP服务，进程编号: {process_number}")
except ImportError:
    print("未找到process_terminator模块，跳过进程终止HTTP服务启动")
except Exception as e:
    print(f"启动进程终止HTTP服务时出错: {e}")
"""

def add_terminator_to_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "process_terminator" in content:
        print(f"文件 {file_path} 已包含进程终止HTTP服务，跳过")
        return
    
    main_pattern = r'if\s+__name__\s*==\s*["\']__main__["\']\s*:(.*?)(\s+main\(\))'
    match = re.search(main_pattern, content, re.DOTALL)
    
    if match:
        new_content = content.replace(match.group(0), 
                                     f'if __name__ == "__main__":{match.group(1)}{TERMINATOR_CODE}{match.group(2)}')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"已向 {file_path} 添加进程终止HTTP服务")
    else:
        print(f"无法在 {file_path} 中找到main()调用，跳过")

def process_all_templates():
    template_dir = os.path.dirname(os.path.abspath(__file__))
    
    python_files = []
    for root, _, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.py') and file not in ['process_terminator.py', 'add_process_terminator.py', 'terminate_server.py', 'add_terminate_support.py']:
                python_files.append(os.path.join(root, file))
    
    for file_path in python_files:
        add_terminator_to_file(file_path)

if __name__ == "__main__":
    process_all_templates()
