////////////////////////////////////////////////////////////////////////
// Copyright (c) 2019,电子科学研究院
// All rights reserved.
//
// 文件名称：Algorithm_.h
// 摘    要： 一致性编队算法基于一致性理论，实现多无人机系统的协同编队控制，保持预定的几何构型。
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

#ifdef Algorithm__LIBRARY
# define Algorithm_SHARED_EXPORT __declspec(dllexport)
#else
# define Algorithm_SHARED_EXPORT __declspec(dllexport)
#endif

#include "vector"
#ifndef Algorithm__H
#define Algorithm__H

class Algorithm_SHARED_EXPORT Algorithm_
{

public:
    //构造函数
    Algorithm_();
	
	//析构函数
	~Algorithm_();
    
    bool Algorithm_(矩阵 F, 函数 Tr, 矩阵 X_0, 矩阵 &formation_pos, 标量 &formation_error);

    //@interface@
	
//@custom_function@
	

};

#endif // Algorithm__H

