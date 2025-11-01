-------------------------------------------------
#
# Project created by QtCreator 2019-06-21T10:15:58
#
#-------------------------------------------------
#注：基于可重用考虑，组件库只能使用纯c++编码，不允许加载qt的任何库和使用qt函数
QT -= core gui

TEMPLATE = lib

DEFINES += Algorithm__LIBRARY

SOURCES += Algorithm_.cpp

HEADERS += Algorithm_.h

CONFIG += plugin

win32{
#windows
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_d

    }else{
    TARGET = ../../../release/models/Algorithm_
    }
}else{
#linux
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_d
    }else{
    TARGET = ../../../release/models/Algorithm_
    }
}
