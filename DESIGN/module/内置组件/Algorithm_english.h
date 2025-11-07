////////////////////////////////////////////////////////////////////////
// Copyright (c) 2019,电子科学研究院
// All rights reserved.
//
// 文件名称：Algorithm_english.h
// 摘    要： 一致性编队算法基于一致性理论，实现多无人机系统的协同编队控制，保持预定的几何构型。1122
//
// 初始参数：
//
// 创建者：吴刚
// 版本： 1.4
//
//
//
////////////////////////////////////////////////////////////////////////
//@cut0@

#ifdef Algorithm_english_LIBRARY
# define Algorithm_englishSHARED_EXPORT __declspec(dllexport)
#else
# define Algorithm_englishSHARED_EXPORT __declspec(dllexport)
#endif

#include "vector"
#ifndef Algorithm_english_H
#define Algorithm_english_H

class Algorithm_englishSHARED_EXPORT Algorithm_english
{

public:
    //构造函数
    Algorithm_english();
	
	//析构函数
	~Algorithm_english();
    
    bool Algorithm_abc(矩阵 去, 函数 Tr, 矩阵 X_0, 矩阵 &formation_pos, 标量 &1111, Any &x);

    //@interface@
	
//@custom_function@
	

};

#endif // Algorithm_english_H

