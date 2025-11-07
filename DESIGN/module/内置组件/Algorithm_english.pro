-------------------------------------------------
#
# Project created by QtCreator 2019-06-21T10:15:58
#
#-------------------------------------------------
#注：基于可重用考虑，组件库只能使用纯c++编码，不允许加载qt的任何库和使用qt函数
QT -= core gui

TEMPLATE = lib

DEFINES += Algorithm_english_LIBRARY

SOURCES += Algorithm_english.cpp

HEADERS += Algorithm_english.h

CONFIG += plugin

win32{
#windows
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_englishd

    }else{
    TARGET = ../../../release/models/Algorithm_english
    }
}else{
#linux
    CONFIG (debug, debug|release) {
    TARGET = ../../../debug/models/Algorithm_englishd
    }else{
    TARGET = ../../../release/models/Algorithm_english
    }
}
