-------------------------------------------------
#
# Project created by QtCreator 2019-06-21T10:15:58
#
#-------------------------------------------------
#注：基于可重用考虑，组件库只能使用纯c++编码，不允许加载qt的任何库和使用qt函数
QT -= core gui

TEMPLATE = lib

DEFINES += Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm_LIBRARY

SOURCES += Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm.cpp

HEADERS += Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm.h

CONFIG += plugin

win32{
#windows
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithmd

    }else{
    TARGET = ../../../release/models/Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm
    }
}else{
#linux
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithmd
    }else{
    TARGET = ../../../release/models/Algorithm_Pheromone-Based Collaborative Reconnaissance Algorithm
    }
}
