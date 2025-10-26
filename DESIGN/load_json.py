import tkinter as tk
from tkinter import ttk, messagebox
import json
import datetime
import os
import re
import sys


class ComponentGenerator:
    def __init__(self, component_name=None, json_path="algorithm_data.json"):

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TFrame", background="#f0f0f0")

        # 存储当前加载的配置
        self.current_config = None
        self.current_algorithm_name = component_name
        self.english_name = None
        self.json_path = json_path
        with open(self.json_path, "r", encoding="utf-8") as file:
            self.algorithms = json.load(file)

    def generate_code(self, initial_type, meta_data):
        if not self.current_algorithm_name:
            messagebox.showwarning("警告", "请先加载组件配置")
            return
        # 尝试提取英文名称
        self.english_name = self.algorithms[self.current_algorithm_name]['english_name']

        category = self.algorithms[self.current_algorithm_name].get('category', '')
        # 使用英文名称
        class_name = 'Algorithm_' + self.english_name

        os.makedirs(f'module\\{category}', exist_ok=True)

        # 生成项目文件
        pro_content = self.generate_project(class_name)
        with open(f'module\\{category}\\{class_name}.pro', 'w', encoding='utf-8') as f:
            f.write(pro_content)

            # 生成头文件
        header_content = self.generate_header(class_name, meta_data, initial_type)
        with open(f'module\\{category}\\{class_name}.h', 'w', encoding='utf-8') as f:
            f.write(header_content)

            # 生成实现文件
        impl_content = self.generate_implementation(class_name, initial_type, meta_data)
        with open(f'module\\{category}\\{class_name}.cpp', 'w', encoding='utf-8') as f:
            f.write(impl_content)

    def generate_project(self, class_name):
        pro_template = """-------------------------------------------------
#
# Project created by QtCreator 2019-06-21T10:15:58
#
#-------------------------------------------------
#注：基于可重用考虑，组件库只能使用纯c++编码，不允许加载qt的任何库和使用qt函数
QT -= core gui

TEMPLATE = lib

DEFINES += {0}_LIBRARY

SOURCES += {0}.cpp

HEADERS += {0}.h

CONFIG += plugin

win32{{
#windows
    CONFIG (debug, debug|release) {{
    TARGET = ../../../debug/models/{0}d

    }}else{{
    TARGET = ../../../release/models/{0}
    }}
}}else{{
#linux
    CONFIG (debug, debug|release) {{
    TARGET = ../../../debug/models/{0}d
    }}else{{
    TARGET = ../../../release/models/{0}
    }}
}}
""".format(class_name)
        return pro_template

    def generate_header(self, class_name, initial_params, initial_type):
        header_template = """////////////////////////////////////////////////////////////////////////
// Copyright (c) 2019,电子科学研究院
// All rights reserved.
//
// 文件名称：{0}.h
// 摘    要： {1}
//
// 初始参数：
//
// 创建者：{2}
// 版本： {3}
//
//
//
////////////////////////////////////////////////////////////////////////
//@cut0@

#ifdef {0}_LIBRARY
# define {0}SHARED_EXPORT __declspec(dllexport)
#else
# define {0}SHARED_EXPORT __declspec(dllexport)
#endif

#include "vector"
#ifndef {0}_H
#define {0}_H

class {0}SHARED_EXPORT {0}
{{

public:
    //构造函数
    {0}();
	
	//析构函数
	~{0}();
    
    bool Algorithm_{4}({5});

    //@interface@
	
//@custom_function@
	

}};

#endif // {0}_H

""".format(class_name, initial_params['description'], initial_params['creator'], initial_params['version'], initial_params['new_algo_name'], initial_type)  # , desc, creator, today, class_name.upper())
        return header_template

    def generate_implementation(self, class_name, initial_type, initial_params):
        impl_template = """
////////////////////////////////////////////////////////////////////////
// Copyright (c) 2019,电子科学研究院
// All rights reserved.
//
// 文件名称：{0}.cpp
// 摘    要： {1}
// 创建者：{2}
// 版本：{3}
//
//
////////////////////////////////////////////////////////////////////////



#include "{0}.h"

{0}::{0}()
{{
    
}}

/////////////////////////////////////////////
//函数名: ~{0}
//函数说明: 析构函数
{0}::~{0}()
{{
}}

bool {0}::Algorithm_{4}({5})
{{

    bool flag = false;
    //此处编写算法逻辑

    return flag;
}}


//@custom_function@

""".format(class_name, initial_params['description'], initial_params['creator'], initial_params['version'], initial_params['new_algo_name'], initial_type)
        return impl_template


def main():
    # 检查命令行参数
    component_name = None
    json_path = "algorithm_data_.json"

    if len(sys.argv) > 1:
        component_name = sys.argv[1]
    if len(sys.argv) > 2:
        json_path = sys.argv[2]

    root = tk.Tk()
    app = ComponentGenerator(root, component_name, json_path)
    root.mainloop()


if __name__ == "__main__":
    main()
