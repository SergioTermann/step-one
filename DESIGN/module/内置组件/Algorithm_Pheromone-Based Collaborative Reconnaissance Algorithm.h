////////////////////////////////////////////////////////////////////////
// Copyright (c) 2019,电子科学研究院
// All rights reserved.
//
// 文件名称：Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm.h
// 摘    要： 一致性编队算法基于一致性理论，实现多无人机系统的协同编队控制，保持预定的几何构型。阿四
//
// 初始参数：
//
// 创建者：郝帅
// 版本： 1.4
//
//
//
////////////////////////////////////////////////////////////////////////
//@cut0@

#ifdef Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm_LIBRARY
# define Algorithm_Pheromone-Based Collaborative Reconnaissance AlgorithmSHARED_EXPORT __declspec(dllexport)
#else
# define Algorithm_Pheromone-Based Collaborative Reconnaissance AlgorithmSHARED_EXPORT __declspec(dllexport)
#endif

#include "vector"
#ifndef Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm_H
#define Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm_H

class Algorithm_Pheromone-Based Collaborative Reconnaissance AlgorithmSHARED_EXPORT Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm
{

public:
    //构造函数
    Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm();
	
	//析构函数
	~Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm();
    
    bool Algorithm_template(bool a, unsigned int Tr, double X_0, Any b, double &formation_pos, std::vector<int> &formation_error);

    //@interface@
	
//@custom_function@
	

};

#endif // Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm_H

