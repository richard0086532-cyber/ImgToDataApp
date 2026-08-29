#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
全自动图表数据识别Agent - shandong_chart_extractor_agent.py
================================================================================
功能：全自动识别图片中的文字、数字、XY轴曲线数据，输出96点CSV
适用：山东电力交易中心电价/负荷曲线截图、PDF转图片
作者：AI Agent
版本：V5.0 (2026-07-26)
    V5.0 “虚线全天被实线遮蔽”锚点差合成兜底（20260503症状驱动）：
        预测≈实际到全天像素级重合的日子，虚线在图上零可见，核掩码
        聚簇与全掩码下方搜索双双失败 → 曲线不足4条 → 负荷面板退化
        拒导 → 无CSV无综合曲线图。新增 _synthesize_dashed_from_anchor：
        tooltip同时给出预测/实际锚点时，以“实线+锚点差”合成虚线
        （形态随实线，锚点时刻精确等于tooltip值，图上印刷峰值由
        峰值守卫再吸附，如84065@11:00）。仅锚点差已知才合成，
        绝不凭空捏造缺测曲线。
        V5.0b：tooltip抬头时间OCR误读防护（"11:00"误判"11:15"），
        与蓝色竖线冲突>0.1h时采信竖线——否则四曲线锚点整体错写
        晚15分钟、峰值84065移位到11:15。
        V5.0c：虚线偏移方向一致性过滤——填充上沿被当成虚线给出
        反向假偏移（05-03预测直调中午-3000假凹陷，tooltip证其应
        在上方+1720）；锚点差>1.5px时丢弃反向样本、虚线在上方时
        跳过下方搜索退路（必读填充），宁交锚点差合成也不读填充。
    V4.9 (2026-07-26)
    V4.9 “峰值标注OCR误读”数字级纠错（用户环境驱动）：
        不同OCR引擎对彩色标注的识别稳定性不同：图上印刷"26960.82"
        在部分环境被读成"20960.81"（6->0、2->1形近误读）。颜色分配
        门控宽至60%，误读值会被直接吸附并全天封顶成错误平台；
        定点OCR通道则以12%门控误拒，真值始终进不了CSV。
        新增 _repair_ocr_number：以曲线像素峰值（圆点/P98）为独立
        量测，对误读数值做形近数字替换（最多2位、替换最少优先、
        误差<=3%采纳），在两个写入点生效——
        1) _targeted_peak_ocr 12%拒写前先纠错；
        2) _snap_price_annotations 吸附写入前，对偏离曲线锚点>5%
           的已分配标注纠错（<=5%不触碰，正确识别环境零影响）。
    V4.8 (2026-07-26)
    V4.8 “别日数据混入当日总表”修复：
        Dashboard截图常带相邻日期的历史小面板（05-02截图里的05-17/
        05-18电量面板）。合并总表虽按主日期取数，但峰值守卫不分日期，
        05-17的标注13468.38被强写进当日电量列、压盖当日峰值14028.61。
        1) 主流程只处理主日期（面板数最多）面板，别日面板不提取、
           不导出、不并入总表（用户明确要求不要5.17/5.18数据）；
        2) 合并表峰值守卫按“列的实际数据来源面板”过滤，纵深防御。
    V4.7 (2026-07-26)
    V4.7 “刻度-标注粘连导致轴标定错误”修复（20260502风电样本驱动）：
        1) Y刻度修复：峰值标注与Y轴刻度粘连（"12,000"+蓝色"10730.09"
           OCR成"12,00730.09"、数值越界被剔除；"0"刻度中心右移被剔除），
           幸存刻度把绘图区错标成2035~10027（真值0~12000），晚间近0
           曲线被钳成平线。按幸存刻度的主导等差数列，对行对齐的剔除
           候选重新赋值补回（±25%间隔对齐、外扩≤1.5间隔）；
        2) X刻度精拟合推广到所有面板：OCR把整行X标签合并成一个文本
           （"00:1503:3006:45..."），按字符相对位置估算像素有系统性
           内缩偏差（风电x_min曾1.333、早间数值整体右移1.08h）；
           刻度标签连通域中心拟合残差<±0.5px；_fit_load_x_axis_by_ticks
           端点改取极值时刻的拟合像素并回传时刻一并校正x_min/x_max。
    V4.6 (2026-07-26)
    V4.6 “出力面板实时出力后半段冻结”修复（20260502样本驱动）：
        出力面板（非市场化/全网发电/风电/太阳能）的实时出力是带半透明
        渐变填充的面积图，线条行经填充深处时被洗淡碎成若干小连通域，
        连通域过滤（保留>最大组件10%）把它们全部丢弃，骨干路径在中午
        前后戛然而止，96点插值把剩余时段钳成恒值直线（05-02三个面板
        实时出力13:15后全部冻结；风电骨干仅123/245列）。V4.6在连通域
        过滤前留存完整掩码，DP骨干生成后沿其两端贪心接续碎片（每列取
        ±25px内最近簇顶、允许≤40列空档），恢复全天覆盖；标注文字紧贴
        峰值位于骨干段内，延伸区无文字，行窗保证不误跳。
        V4.6b：延伸改用开运算前原始掩码（2px细线被3x3开运算整体腐蚀，
        全网发电预测出力上午段因此全丢、被钳成峰值直线69868.99），行窗
        随空档自适应放大25+1.2*gap、空档容忍60列，找回稀疏细线段。
    V4.4 (2026-07-25) “CSV对比PNG不准”精度修复：
        1) 青色系HSV双区间(H72~79/S>=55 + H80~95/S>=65)在H=80、S=55~64
           处存在缺口，抗锯齿线顶像素漏检，曲线顶边下移1~2px(约500~
           1000MW)。统一为H72~96/S>=48；橙色下限S65->50同理；
        2) tooltip锚点整体缩放阈值20%->5%：局部污染(如11:15读到圆环
           顶44624)曾把全天曲线压低8%，超阈值只写锚点不再全局缩放；
        3) 经像素级比对确认：V4.3的CSV与输入截图20260501.png自身像素
           吻合(±500)，与参考图image(3).png的差异源自两张截图本身
           数据不一致(同日11:15 tooltip相同，部分时段曲线重绘)；
        4) X轴右端延出修正：蓝色X轴右端可能比23:00刻度多延一截
           (实测image(3)延出26px)，直接拿蓝线端点当23:00会使晚间时段
           采样位置偏晚、读数偏低(22:15曾58708 vs 真值62663)。V4.4用
           hover蓝色竖线x像素+tooltip时间双锚点反推px/h重算右端点，
           修正量>3px且<=10%跨度才采纳；完整Dashboard无延出自动跳过；
        5) hover圆环畸变区挖除：ECharts在hover竖线处对每条曲线绘制半径
           ~13px空心圆环，上/下弧会被当成曲线(实际全网11:00曾读圆环顶
           86,964，真值~81,500；预测直调曾读下弧37,878，真值~40,300；
           远处“实线+虚线对”也满足圆环判据被误拉到两线中点，14:15实线
           曾偏低~3000)。V4.4提取前挖除竖线±16px列由插值桥接、锚点写
           精确值，圆环校正限定竖线附近(电价面板真圆环不受影响)；
        6) 虚线提取起点实线下方+2->+4px且簇宽>=2px：+2会抓到实线自身
           下边缘(image(3)14:15预测直调曾读49,090，真值46,487)；1px
           抗锯齿残丝跳过。Dashboard虚线为低饱和细线、与实线近乎粘连，
           高饱和核掩码两张图不可通用，故仍用全掩码+宽度过滤；
        6b) X轴刻度标签连通域拟合px=a*t+b（残差<±0.5px），优先于hover
           双锚点；蓝线左右端均有1~26px留白，端点当刻度用会让采样偏位
           (Dashboard右端延出13px、image(3)延出26px)；
        7) V4.5(20260502样本驱动)：预测≈实际的日子里虚线与实线近乎重合、
           且虚线可能在实线上方(预测>实际)。原“实线下方搜索”找不到橙
           色虚线(命中<30列)导致退化拒导CSV；青色虚线则误读填充顶
           (低~5400)。V4.5主路改用高饱和核掩码在实线±35px双侧量测
           “虚线-实线”偏移并全天插值合成(填充S55~62在核掩码中不可见)，
           命中<12列才退回全掩码下方老逻辑(适配20260501低饱和细虚线)；
           兜底实线由簇中心改簇顶(填充在掩码内时中心偏低20~30%)。
        7) 锚点整体缩放阈值5%->1.5%：视觉轴+hover双锚点标定已达像素级，
           真实系统偏差<1%；锚点位于圆环畸变区，其读数偏差是局部污染，
           整体缩放会把~1.4%局部误差放大成全天系统偏差(曾全天-860MW)。
    V4.3 (2026-07-25)
    V4.3 “负荷面板CSV仍为14000直线”根源修复：
        1) 【根因】self._last_axis 只在非负荷面板的 extract_curves() 中
           设置，负荷面板专用分支从不更新它；插值阶段于是沿用上一面板
           （风电 Y=[1989.28,14000.00]）的陈旧轴做裁剪，37000~84000的
           四条负荷曲线被clip成14000.00常数。V4.3把坐标轴直接挂到每条
           曲线(curve._axis)，插值优先使用曲线自带轴，彻底消除全局
           陈旧状态；负荷面板每次换轴后同步刷新_last_axis；
        2) 【tooltip】“40,347.87/82,446.01”这类完整千分位数值必须直接
           解析，禁止“40→40000”式的×1000兜底抢占；拆分碎片
           “40 + 347.87”支持2~3段拼接；
        3) 【非市场化13941】平台型曲线峰值易被圆环/同色文字污染
           (20780.50)，定点OCR验收基准由全局max改为P98稳健峰值，
           13941.00与平台值差<1%即可通过并在00:15落盘；
        4) 【峰值时点】圆点吸附后再以曲线局部最高点复核（±0.6h窗口），
           并量化到最近15分钟网格，消除圆心检测~3px右偏造成的
           09:00/21:15/11:15等一个时点偏差；
        5) 【导出守卫】负荷面板CSV导出前强制退化校验，仍退化时启用
           独立视觉兜底重提；再失败则拒绝落盘直线CSV。
    V4.2 “吸附成功但CSV未落盘”一致性修复：
        1) 所有面板处理完成后，使用最终内存曲线二次重写每个面板CSV，
           防止load_summary正确而load_96points仍为旧直线；
        2) 峰值吸附后记录(值,时间)为canonical peak guard，合并表导出后
           再逐项校验并强制落盘；
        3) 强制实时出清电量12173.47@00:15、非市场化机组预测出力
           13941.00@00:15等OCR峰值在面板CSV和合并CSV保持一致；
        4) 新增导出后回读校验报告，能直接看出哪一个CSV仍不一致。
    V4.1 完整Dashboard负荷面板真实日志修复：
        1) 不再用“legend下方第一条线必是边框”的规则；改为用
           100000/80000/60000/40000/20000网格线等距序列评分，
           完整Dashboard可正确选择1078而不是1115；
        2) tooltip拆分OCR支持“40 + 347.87”、“82 + 446”拼接复原，
           并从粘连标题“11:预测/实际负荷及出力”恢复11:15；
        3) 完整Dashboard负荷面板Y轴OCR为空时，仍可凭视觉网格序列和
           tooltip恢复四条曲线；
        4) 继续保留V4.0的退化检查，恢复失败才拒绝导出。
    V4.0 负荷图“四条曲线变直线”终极修复：
        1) 视觉轴候选线先按行聚类，区分“绘图区顶边框”和真正的
           100,000 MW网格线，避免把legend下方分隔线误作Y轴上限；
        2) OCR Y轴刻度作为视觉轴候选的优先校验，tooltip遮挡时再用
           网格线序列兜底；
        3) 96点插值后同时检查“数值恒定”和“唯一值过少”，任何恢复失败
           都会明确报警，不再静默输出14000/1989直线；
        4) 四条曲线必须满足形状和tooltip锚点校验后才导出负荷汇总。
    V3.9 负荷单图真实数据复核修复：
        1) 新增负荷面板“视觉轴标定”：直接识别蓝色X轴端点、0~100000网格区，
           不再依赖可能被tooltip污染的OCR刻度；
        2) 在插值后再次检查四条负荷是否退化为同一常数，防止1989.28被
           边界填充到全部96点；
        3) 优先用视觉轴重提负荷曲线，再用tooltip四值做整体比例校正和
           11:15精确写入；
        4) 兼容PaddleOCR把tooltip“名称”和“数值”拆成两条识别，
           自动按同行/下一行最近数值补齐；
        5) 负荷汇总CSV/PNG仍固定96行，曲线形状以PNG真实图像为准。
    V3.8 2026-05-01二次复核修复：
        1) 负荷面板单独裁剪图中，图例落在绘图区上方，旧版把图例色块当曲线，
           导致四条负荷曲线变成1989.28常数；新增图例/遮挡框剔除；
        2) 峰值标注不再被圆点锚点否决，确保非市场化机组预测出力13941.00
           这类平台峰值始终进入CSV；
        3) Hough圆点候选由“首个阈值命中即停止”改为多阈值候选合并评分，
           修复68316.00被定位到10:45/13:15而非11:00的问题；
        4) 多色面板严格限制跨色峰值分配，防止蓝色的68316.00被写到
           橙色“全网发电实时出力”列；
        5) 新增负荷汇总CSV/PNG导出，包含11:15 tooltip锚点校验。
    V3.7 2026-05-01专项复核修复：
        1) 峰值时间不再用“标注文字左边缘”估算，改为同色空心圆点中心定位，
           吸附到最近的96点时刻；修复太阳能实时15618.55、非市场化13941.00/
           43647.98、日前电价538.50等峰值整体错一个/多个15分钟时点的问题；
        2) 峰值OCR候选改用圆点像素反算值做锚点，解决全网实时68717.84被误读/
           误吸附为68141.84/67918.18的问题；
        3) 负荷面板标题被tooltip遮挡时，通过“预测/实际直调负荷、预测/实际
           全网负荷”图例+X/Y轴刻度反推面板，补齐4条负荷曲线；
        4) 负荷面板预测/实际为同色系，仅靠颜色无法区分：新增实线/虚线分离，
           实线=实际、虚线=预测；
        5) 合并总表固定输出完整17列、严格96行，并打印关键极值复核表。
    V3.6 定点二次OCR：全图OCR漏读/熔读的峰值标注（橙字压橙线小数点被吞、
        蓝字与Y轴刻度熔合如'14,020173.47'），按轴标定把曲线峰值换算回像素
        位置，裁剪全轴宽横条+目标色系像素隔离+4x放大，复用OCR引擎定向识别；
        候选须经原图同色系patch校验+与曲线峰值差<12%门控（宁可跳过不可错绑），
        通过后与来源曲线直接绑定吸附；不做曲线减除（文字与曲线同色会同被擦除）
    V3.5 圆环标记校正：数据点空心圆让DP路径骑圆弧虚高/虚低一个半径，
        圆环列签名(同列2簇,上簇sp0<=8,簇间gap<=16)+两簇内沿中点=圆心+
        >=2连续列成run取中位数+run间线性插值，路径偏离>1.5px改写回期望值
    V3.4 峰值吸附颜色优先混合版：候选三通道（正常/粘连复原/漏点复原）+
        两阶段1:1贪心（同色系60%先行、纯数值30%兜底）+tooltip冒号行排除+
        坐标轴fallback面板整面板不吸附
    V3.1 山东市场规则钳制：出清电价下限-80元/MWh、出力/负荷/电量非负；
        修复峰值吸附漏触发：标注".00"值被is_integer误杀（改查原文小数点）、
        位置边距±15→±30px（标注常贴绘图区上沿）；
        时间标签24:00修正；坐标轴fallback面板不并入合并总表
    V3.2 标注吸附按色系家族匹配（橙/黄同族：黄色标注可命中橙色曲线，
        修复15618.55/43647.98/11231.69/68717.84全部漏吸附）+最近值兜底；
        标注时间改用文本左缘估算（标签在峰值点右侧）；
        green色相下限回缩55（35会误捕填充渐变色产生杂讯曲线）
    V3.0 96点时间轴修正为00:15~24:00（现货市场标准）；
        HSV饱和度/亮度阈值下调（修复洗淡面板漏抓：全网发电蓝线S<80不可见）；
        峰值标注吸附推广到所有折线面板（68316/68717.84/43647.98/13941.00/
        11231.69/12173.47/15618.55等当日最大值标签全部利用）；
        负荷面板4曲线配色映射（直调=青绿系、全网=橙黄系）+合并表新增全网负荷列
    V2.9 新增跨面板合并总表（*_merged_96points.csv）：电价/电量/直调负荷/
        太阳能/风电/非市场化/全网发电全列合并；多日期面板自动取多数日期
    V2.8 插值从CubicSpline改为PCHIP保形插值（跨数据空档不再振荡出假谷，
        如实时电价晚间被甩到0的问题；非市场化37297平台同源）；
        电价面板禁用savgol平滑（现货电价是阶梯函数，保留台阶形态）
    V2.7 DP路径追踪替代逐列取点（抗绘图区内标注文字污染，如绿色"538.50"）；
        移除medfilt（保护真实尖峰）；电价面板峰值标注吸附+全天封顶
        （曲线峰值精确对齐图上标注值，如实时715.93、日前538.50）
    V2.6 修复：太阳能填0标志在插值前被提前复位（顺序错误）；
        同一条曲线被orange/yellow相邻色相拆成两条导致同名撞车——
        映射后按名称去重，保留像素点多者
    V2.5 修复：跨度过滤从"ROI全宽35%"改为"绘图区25%"（太阳能白天曲线152列
        被168.7阈值误杀）；异色曲线不参与重合去重；太阳能夜间缺数段填0；
        各过滤环节增加原因打印
    V2.4 修复：插值数据空段改为边缘保持不外推（太阳能夜间假平台59966→归0）；
        连通域过滤绘图区内部标注文字（蓝色"13941.00"等），只保留曲线大组件
    V2.3 修复：峰值标注文字（蓝色"715.93"等）与曲线同色导致曲线被拉飞/误删——
        颜色掩码先裁剪到坐标轴标定的绘图区内（区外图例/标注像素清零），
        再加窗口3中值滤波杀灭残留文字细笔画毛刺
    V2.2 修复：曲线像素（裁剪相对坐标）与坐标轴像素（全图绝对坐标）系错位，
        导致所有曲线映射超范围被剔除（多面板模式致命bug）；
        X轴刻度排除Y轴"0"标签和"05.11"日期标签；跳过出清信息柱状图面板
    V2.1 修复：text_data逐面板覆盖导致后续面板无OCR数据（引入text_data_all）；
        面板检测改为标题锚定法（相邻白卡粘连时仍能正确拆分）；
        X轴整行合并时间标签（"00:15 03:30 ..."）逐个提取并按字符位置估算像素
    V1.1 兼容 PaddleOCR 3.x API（自动适配 2.x / 3.x）
    V1.2 禁用oneDNN，规避Windows推理Bug
    V1.3 坐标轴鲁棒标定（X轴限0~24h时间刻度、Y轴线性拟合+离群剔除）、
        曲线形状/范围/重合三重过滤（杜绝文字轮廓被识别为曲线）、
        插值结果裁剪到轴范围、警告去重限量
    V2.0 多面板架构：自动检测Dashboard多窗口截图中的各图表面板
        （白色卡片定位+标题OCR+子类型/日期识别），逐面板独立标定提取；
        全图OCR仅一次；HSV色相配色匹配Dashboard真实曲线颜色；
        曲线名称按图例固定配色自动映射（绿=日前出清电价、蓝=实时出清电价等）

核心能力：
1. 自动检测图表区域（ROI）
2. PaddleOCR识别坐标轴刻度文字
3. OpenCV自动追踪曲线像素
4. 像素坐标→实际数值自动映射
5. 按固定X间隔（15分钟=96点）插值输出
6. 多曲线同时提取（日前/实时/负荷等）
7. 置信度评分与人工校验标记

依赖安装：
    pip install paddlepaddle paddleocr opencv-python numpy pandas matplotlib scipy
    # 如需GPU加速：pip install paddlepaddle-gpu
================================================================================
"""

import os
import sys
import re
import json
import math
import argparse
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

import cv2
import numpy as np
import pandas as pd
from scipy import interpolate
from scipy.signal import savgol_filter

# ==============================================================================
# 规避 paddlepaddle 3.x + Windows + oneDNN 的已知推理Bug：
# NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
# [pir::ArrayAttribute<pir::DoubleAttribute>]
# 必须在 import paddle / paddleocr 之前设置
# ==============================================================================
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")

# PaddleOCR
from paddleocr import PaddleOCR

# Matplotlib（可选，用于调试可视化）
try:
    import matplotlib
    matplotlib.use('Agg')  # 无GUI后端
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False


def _cn_font_prop():
    """返回中文字体属性；不修改全局rcParams，避免中文汇总图出现方框。"""
    if not MPL_AVAILABLE:
        return None
    for name in ("Noto Sans CJK SC", "Microsoft YaHei", "SimHei",
                 "WenQuanYi Zen Hei", "Arial Unicode MS"):
        try:
            path = fm.findfont(name, fallback_to_default=False)
            if path and os.path.exists(path):
                return fm.FontProperties(fname=path)
        except Exception:
            continue
    return None


warnings.filterwarnings('ignore')

SCRIPT_VERSION = "V4.4"

# ==============================================================================
# 配置常量
# ==============================================================================

DEFAULT_CONFIG = {
    "ocr": {
        "use_gpu": False,
        "lang": "ch",
        "det_model_dir": None,
        "rec_model_dir": None,
        "cls_model_dir": None,
        "drop_score": 0.5,
        "use_angle_cls": True,
    },
    "chart": {
        "min_chart_area_ratio": 0.05,      # 图表区域最小占图比例
        "axis_detection_margin": 20,        # 坐标轴检测边距
        "curve_color_tolerance": 30,       # 曲线颜色容差
        "min_curve_points": 50,            # 最小曲线点数
        "interpolation_method": "cubic",   # 插值方法
        "output_points": 96,               # 输出点数（96点=15分钟间隔）
        "smoothing_window": 7,             # Savitzky-Golay平滑窗口
        "smoothing_polyorder": 3,          # 平滑多项式阶数
    },
    "validation": {
        "max_price": 1500.0,               # 电价上限（元/MWh）
        "min_price": -200.0,               # 电价下限
        "max_load_mw": 100000.0,           # 负荷上限（MW）
        "continuity_threshold": 0.15,      # 连续性阈值（相对跳变）
    }
}

# 常见曲线颜色定义（HSV格式，匹配山东电力交易中心Dashboard配色）
# 每个颜色可含多个 (lower, upper) 区间（如红色跨0°）
HSV_CURVE_COLORS = {
    # S/V阈值已调低（S>40, V>60）：部分面板线条被半透明白层洗淡（全网发电等），
    # 高阈值会漏抓；灰白网格线S<20仍被排除
    "red":    [((0, 40, 60), (8, 255, 255)), ((170, 40, 60), (179, 255, 255))],
    "orange": [((9, 40, 60), (24, 255, 255))],
    "yellow": [((25, 40, 60), (34, 255, 255))],
    "green":  [((55, 40, 60), (85, 255, 255))],
    "cyan":   [((86, 40, 60), (94, 255, 255))],
    "blue":   [((95, 40, 60), (125, 255, 255))],
    "purple": [((126, 40, 60), (165, 255, 255))],
}

# 面板标题关键词 -> 面板类型（山东电力交易中心Dashboard）
PANEL_TITLE_MAP = [
    ("负荷及出力", "load"),
    ("出清信息", "info"),
    ("市场出清", "clearing"),
]

# 面板类型 -> 曲线颜色名映射（该Dashboard图例固定配色）
PANEL_CURVE_MAP = {
    "price":  {"green": "日前出清电价", "blue": "实时出清电价"},
    "energy": {"blue": "实时出清电量"},
    # 负荷面板（负荷tab，4条曲线，色点采样：直调=青/绿色系，全网=橙/黄色系）
    "load":   {"cyan": "预测直调负荷", "green": "实际直调负荷",
               "yellow": "预测全网负荷", "orange": "实际全网负荷"},
    # 出力面板（出力tab，2条曲线：蓝=预测，橙/黄=实时）
    "load_gen": {"blue": "预测出力", "orange": "实时出力", "yellow": "实时出力"},
}

# 合并总表：面板子类型 -> {曲线名: 合并列名}
MERGE_COLUMN_MAP = {
    "price":           {"日前出清电价": "日前出清电价", "实时出清电价": "实时出清电价"},
    "energy":          {"实时出清电量": "实时出清电量"},
    "load":            {"预测直调负荷": "预测直调负荷", "实际直调负荷": "实际直调负荷",
                        "预测全网负荷": "预测全网负荷", "实际全网负荷": "实际全网负荷"},
    "load_太阳能发电":  {"预测出力": "太阳能发电预测出力", "实时出力": "太阳能发电实时出力"},
    "load_风电":       {"预测出力": "风力发电预测出力", "实时出力": "风力发电实时出力"},
    "load_非市场化机组": {"预测出力": "非市场化机组预测出力", "实时出力": "非市场化机组实时出力"},
    "load_全网发电":    {"预测出力": "全网发电预测出力", "实时出力": "全网发电实时出力"},
}

# 合并总表列顺序
MERGE_COLUMN_ORDER = [
    "日前出清电价", "实时出清电价", "实时出清电量",
    "预测直调负荷", "实际直调负荷", "预测全网负荷", "实际全网负荷",
    "太阳能发电预测出力", "太阳能发电实时出力",
    "风力发电预测出力", "风力发电实时出力",
    "非市场化机组预测出力", "非市场化机组实时出力",
    "全网发电预测出力", "全网发电实时出力",
]

# ==============================================================================
# 数据类定义
# ==============================================================================

@dataclass
class AxisInfo:
    """坐标轴信息"""
    x_min: float = 0.0
    x_max: float = 24.0
    y_min: float = 0.0
    y_max: float = 1000.0
    x_label: str = ""
    y_label: str = ""
    x_unit: str = "h"
    y_unit: str = "元/MWh"
    x_pixel_range: Tuple[int, int] = (0, 100)
    y_pixel_range: Tuple[int, int] = (100, 0)  # Y轴像素通常从上到下
    confidence: float = 0.0

@dataclass
class CurveData:
    """单条曲线数据"""
    name: str = ""
    color_name: str = ""
    points: List[Tuple[float, float]] = field(default_factory=list)  # (x, y)实际值
    pixel_points: List[Tuple[int, int]] = field(default_factory=list)  # (px, py)像素
    confidence: float = 0.0
    is_valid: bool = True
    error_msg: str = ""

@dataclass
class ExtractionResult:
    """提取结果"""
    image_path: str = ""
    chart_roi: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    axis_info: AxisInfo = field(default_factory=AxisInfo)
    curves: List[CurveData] = field(default_factory=list)
    text_data: List[Dict] = field(default_factory=list)
    output_csv: str = ""
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0


# ==============================================================================
# 核心Agent类
# ==============================================================================

class ChartExtractorAgent:
    """
    全自动图表数据提取Agent

    工作流程：
    1. 图像预处理（去噪、增强）
    2. 图表区域自动检测（ROI）
    3. OCR识别坐标轴刻度与标签
    4. 自动标定坐标系（像素→实际值映射）
    5. 曲线自动追踪与提取
    6. 数据插值与平滑
    7. 结果验证与输出
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_CONFIG
        self.ocr_engine = None
        self._init_ocr()

    def _init_ocr(self):
        """初始化PaddleOCR引擎（自动适配 2.x / 3.x API）"""
        ocr_cfg = self.config["ocr"]
        print("[INFO] 正在初始化PaddleOCR引擎...")
        # 抑制 PaddleOCR 的冗余日志
        import logging
        logging.getLogger("ppocr").setLevel(logging.WARNING)
        logging.getLogger("paddle").setLevel(logging.WARNING)
        logging.getLogger("paddlex").setLevel(logging.WARNING)

        # 检测 PaddleOCR 大版本
        import paddleocr as _po
        ver = getattr(_po, "__version__", "2.0.0")
        try:
            major = int(str(ver).split(".")[0])
        except ValueError:
            major = 2
        self._ocr_v3 = major >= 3
        self._drop_score = float(ocr_cfg.get("drop_score", 0.5))
        print(f"[INFO] PaddleOCR版本: {ver} ({'v3 API' if self._ocr_v3 else 'v2 API'})")

        if self._ocr_v3:
            # ============================================================
            # PaddleOCR 3.x：已移除 use_gpu / drop_score / show_log /
            # use_angle_cls / *_model_dir 等老参数
            # ============================================================
            # 再次确保禁用 oneDNN（Windows推理Bug规避）
            os.environ["FLAGS_use_mkldnn"] = "0"
            os.environ["FLAGS_use_onednn"] = "0"

            kwargs = dict(
                lang=ocr_cfg.get("lang", "ch"),
                use_doc_orientation_classify=False,   # 替代 use_angle_cls
                use_doc_unwarping=False,
                use_textline_orientation=False,       # 图表文字均为水平，关闭可提速30%+
            )
            if ocr_cfg.get("use_gpu", False):
                kwargs["device"] = "gpu"
            # 优先尝试显式禁用 mkldnn（部分 3.x 版本支持该参数，不支持则自动回退）
            try:
                self.ocr_engine = PaddleOCR(enable_mkldnn=False, **kwargs)
            except (ValueError, TypeError):
                self.ocr_engine = PaddleOCR(**kwargs)
        else:
            # ============================================================
            # PaddleOCR 2.x：老参数
            # ============================================================
            self.ocr_engine = PaddleOCR(
                use_gpu=ocr_cfg.get("use_gpu", False),
                lang=ocr_cfg.get("lang", "ch"),
                det_model_dir=ocr_cfg.get("det_model_dir"),
                rec_model_dir=ocr_cfg.get("rec_model_dir"),
                cls_model_dir=ocr_cfg.get("cls_model_dir"),
                drop_score=self._drop_score,
                use_angle_cls=ocr_cfg.get("use_angle_cls", True),
                show_log=False,
            )
        print("[INFO] PaddleOCR引擎初始化完成")

    def _run_ocr(self, img: np.ndarray) -> List:
        """
        统一OCR调用入口，屏蔽 2.x / 3.x 差异。
        始终返回旧版格式: [[bbox, (text, score)], ...]
        """
        if getattr(self, "_ocr_v3", False):
            # PaddleOCR 3.x: predict() 返回 OCRResult 对象列表
            try:
                results = self.ocr_engine.predict(img)
            except Exception:
                # 部分 3.x 版本仍保留 ocr() 接口
                results = self.ocr_engine.ocr(img)

            lines = []
            if not results:
                return lines

            for res in results:
                # 兼容 dict 访问 / .json 属性两种形式
                if hasattr(res, "json"):
                    data = res.json.get("res", res.json)
                elif isinstance(res, dict):
                    data = res
                else:
                    data = dict(res)

                texts = data.get("rec_texts", []) or []
                scores = data.get("rec_scores", []) or []
                polys = (data.get("rec_polys") if data.get("rec_polys") is not None
                         else data.get("dt_polys", [])) or []

                for box, text, score in zip(polys, texts, scores):
                    score = float(score)
                    if score < self._drop_score:      # 手动实现 drop_score 过滤
                        continue
                    if hasattr(box, "tolist"):
                        box = box.tolist()
                    box = [[float(p[0]), float(p[1])] for p in box]
                    lines.append([box, (str(text), score)])
            return lines
        else:
            # PaddleOCR 2.x: ocr() 返回 [[ [bbox,(text,score)], ... ]]
            result = self.ocr_engine.ocr(img, cls=True)
            if not result or result[0] is None:
                return []
            return result[0]

    # --------------------------------------------------------------------------
    # 步骤1: 图像预处理
    # --------------------------------------------------------------------------
    def preprocess_image(self, image_input) -> np.ndarray:
        """
        读取并预处理图像（支持文件路径或bytes）

        Args:
            image_input: 文件路径(str)或图片bytes

        Returns:
            预处理后的BGR图像
        """
        if isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self._source_name = "upload"
        else:
            img = cv2.imread(str(image_input))
            self._source_name = str(image_input)
        if img is None:
            raise ValueError(f"无法读取图像: {image_input[:50] if isinstance(image_input, bytes) else image_input}")

        # 保持原始尺寸用于后续处理
        self.original_shape = img.shape

        # 如果图像太大，等比例缩放以提高处理速度
        max_dim = 3000
        h, w = img.shape[:2]
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            self.scale_factor = scale
        else:
            self.scale_factor = 1.0

        self.processed_shape = img.shape
        print(f"[INFO] 图像尺寸: {w}x{h} -> 处理后: {img.shape[1]}x{img.shape[0]}, 缩放因子: {scale:.3f}")
        return img

    # --------------------------------------------------------------------------
    # 步骤2: 图表区域自动检测（ROI）
    # --------------------------------------------------------------------------
    def detect_chart_roi(self, img: np.ndarray) -> Tuple[int, int, int, int]:
        """
        自动检测图表主体区域

        策略：
        1. 检测图像中的最大矩形区域（排除边缘）
        2. 基于线条密度和颜色分布判断图表区域
        3. 返回 (x, y, w, h)
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 方法1: 基于边缘密度检测
        edges = cv2.Canny(gray, 50, 150)

        # 膨胀以连接边缘
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        edges_dilated = cv2.dilate(edges, kernel, iterations=2)

        # 查找轮廓
        contours, _ = cv2.findContours(edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 筛选大轮廓
        min_area = w * h * self.config["chart"]["min_chart_area_ratio"]
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        if not valid_contours:
            #  fallback: 使用整图减去边缘
            margin = int(min(w, h) * 0.05)
            return (margin, margin, w - 2*margin, h - 2*margin)

        # 选择最大的轮廓
        largest = max(valid_contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(largest)

        # 微调：确保包含坐标轴标签
        margin = self.config["chart"]["axis_detection_margin"]
        x = max(0, x - margin)
        y = max(0, y - margin)
        bw = min(w - x, bw + 2*margin)
        bh = min(h - y, bh + 2*margin)

        print(f"[INFO] 检测到图表ROI: ({x}, {y}, {bw}, {bh})")
        return (x, y, bw, bh)

    # --------------------------------------------------------------------------
    # 步骤3: OCR识别坐标轴
    # --------------------------------------------------------------------------
    def extract_axis_info(self, img: np.ndarray, roi: Tuple[int, int, int, int],
                          texts: Optional[List[Dict]] = None) -> AxisInfo:
        """
        使用OCR识别坐标轴刻度，建立像素→实际值映射（V2 鲁棒版）

        Args:
            img: 全图
            roi: (x, y, w, h) 图表区域
            texts: 可选，全图OCR结果（多面板模式传入，避免重复OCR）

        策略：
        1. X轴固定为时间轴：只接受 0~24 的刻度值（含 "HH:MM" 格式），
           杜绝图例/数据标签里的大数字（如60000）污染
        2. Y轴只取图表左侧的数字刻度，优先限定在电价合理范围内，
           用最小二乘线性拟合+离群点剔除，抗OCR误读（如14020173.47）
        """
        x, y, w, h = roi

        if texts is None:
            # 单图模式：对ROI区域单独OCR
            roi_img = img[y:y+h, x:x+w]
            ocr_result = self._run_ocr(roi_img)
            texts = self._build_text_entries(ocr_result, x, y)
        else:
            # 多面板模式：从全图OCR结果中筛选落在本面板内的文本（免重复OCR）
            texts = [t for t in texts
                     if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h]

        self.text_data = texts

        if not texts:
            print("[WARN] 本区域无任何OCR文本，使用默认值")
            _ax = AxisInfo(
                x_min=0, x_max=24, y_min=0, y_max=1000,
                x_pixel_range=(x, x + w), y_pixel_range=(y + h, y)
            )
            _ax.used_fallback = True
            return _ax
        val_cfg = self.config["validation"]
        axis = AxisInfo()

        # ==================== X轴：时间轴 0~24h ====================
        x_ticks = []
        x_ticks_hm = []   # V4.3：仅HH:MM格式刻度（可靠）
        x_ticks_int = []  # V4.3：裸整数刻度（易混入Y轴"0"等伪刻度）
        for t in texts:
            if t["center_y"] < y + h * 0.75:
                continue  # 只取图表底部区域
            # OCR常把整行X标签合并成一个文本（如 "00:15 03:30 06:45 ..."），
            # 用finditer逐个提取，并按字符相对位置估算各标签的像素X
            matches = list(re.finditer(r'(\d{1,2})\s*[:：]\s*(\d{2})', t["text"]))
            if matches:
                xs_bb = [p[0] for p in t["bbox"]]
                x0, x1 = min(xs_bb), max(xs_bb)
                txt_len = max(len(t["text"]), 1)
                for m in matches:
                    hh, mm = int(m.group(1)), int(m.group(2))
                    if not (0 <= hh <= 24 and 0 <= mm < 60):
                        continue
                    rel = (m.start() + m.end()) / 2 / txt_len
                    px = x0 + rel * (x1 - x0)
                    x_ticks_hm.append((px, hh + mm / 60.0))
            elif (t["numeric_value"] is not None
                  and 0 <= t["numeric_value"] <= 24
                  and float(t["numeric_value"]).is_integer()      # 排除 "05.11" 等日期/小数
                  and t["center_x"] > x + w * 0.12):               # 排除Y轴刻度(如底部的"0")
                x_ticks_int.append((t["center_x"], float(t["numeric_value"])))
        # V4.3：HH:MM刻度>=3个时，裸整数刻度一律视为Y轴"0"等伪刻度剔除
        # （真实案例：风电面板Y轴"0"@564被当成0:00，X拟合被拉偏到-0.61~22.65，
        # 峰值时点整体右移一个15分钟）
        if len(x_ticks_hm) >= 3:
            x_ticks = x_ticks_hm
        else:
            x_ticks = x_ticks_hm + x_ticks_int
        x_ticks = self._dedupe_ticks(x_ticks)

        if len(x_ticks) >= 2:
            px = [p for p, _ in x_ticks]
            vv = [v for _, v in x_ticks]
            # V4.3：时间刻度用Theil-Sen中位数斜率拟合，抗文字中心偏移/伪刻度
            a, b = self._fit_time_map(px, vv)
            p_min, p_max = min(px), max(px)
            axis.x_pixel_range = (int(p_min), int(p_max))
            axis.x_min = a * p_min + b
            axis.x_max = a * p_max + b
            print(f"[INFO] X轴时间刻度: {len(x_ticks)}个 "
                  f"(范围 {axis.x_min:.2f}~{axis.x_max:.2f} h)")
            print(f"[DEBUG] X刻度明细(像素,值): {[(round(p), round(v, 2)) for p, v in x_ticks]}")
        else:
            # 默认：0-24小时，取ROI中部偏右区域
            axis.x_min, axis.x_max = 0.0, 24.0
            axis.x_pixel_range = (x + int(w * 0.06), x + int(w * 0.97))
            print("[WARN] X轴时间刻度不足2个，使用默认 0~24h 映射")

        # ==================== Y轴：左侧数值刻度 ====================
        y_cand = [(t["center_y"], t["numeric_value"]) for t in texts
                  if t["numeric_value"] is not None and t["center_x"] < x + w * 0.12]
        y_cand = self._dedupe_ticks(y_cand)

        # 优先使用电价合理范围内的刻度（过滤OCR误读的超大值）
        y_in_range = [(p, v) for p, v in y_cand
                      if val_cfg["min_price"] <= v <= val_cfg["max_price"]]
        y_use = y_in_range if len(y_in_range) >= 2 else y_cand
        if len(y_in_range) < 2 and len(y_cand) >= 2:
            print("[WARN] 左侧刻度不在电价常规范围内，按负荷/其他数值轴处理")
        print(f"[DEBUG] Y左侧全部刻度(像素,值): {[(round(p), round(v, 2)) for p, v in y_cand]}")
        print(f"[DEBUG] Y采用刻度(像素,值): {[(round(p), round(v, 2)) for p, v in y_use]}")

        if len(y_use) >= 2:
            # V4.7：补回与峰值标注粘连被误剔除的刻度（如风电"12,00730.09"
            # 与"0"），再重新拟合——否则顶/底刻度缺失会把绘图区标错
            y_repaired = self._repair_y_ticks(y_use, texts, x, w)
            if y_repaired is not None:
                y_use = y_repaired
            py = [p for p, _ in y_use]
            vv = [v for _, v in y_use]
            a, b = self._fit_linear_map(py, vv)
            p_top, p_bottom = min(py), max(py)
            v_top = a * p_top + b        # 顶部像素对应的值
            v_bottom = a * p_bottom + b  # 底部像素对应的值
            axis.y_pixel_range = (int(p_top), int(p_bottom))
            axis.y_max = max(v_top, v_bottom)
            axis.y_min = min(v_top, v_bottom)
            print(f"[INFO] Y轴数值刻度: {len(y_use)}个 "
                  f"(范围 {axis.y_min:.2f}~{axis.y_max:.2f}，"
                  f"剔除{len(y_cand) - len(y_use)}个越界值)")
        else:
            axis.y_min, axis.y_max = 0.0, 1000.0
            axis.y_pixel_range = (y + int(h * 0.08), y + int(h * 0.92))
            axis.used_fallback = True
            print("[WARN] Y轴有效刻度不足2个，使用默认 0~1000 映射")

        # ==================== V4.7：X轴刻度标签连通域精拟合 ====================
        # OCR把整行X标签合并成一个文本时，按字符相对位置估算像素有系统性
        # 内缩偏差（首/末标签最明显，风电曾x_min=1.333偏移+1.08h，早间
        # 数值整体右移1小时）；刻度标签连通域中心拟合残差<±0.5px。
        # 放在Y轴标定之后（需要y_pixel_range定位标签带）；负荷面板稍后
        # 经_refine_load_x_axis_by_hover再校一遍，结果一致自动跳过。
        tick_fit = self._fit_load_x_axis_by_ticks(img, roi, axis, texts)
        if tick_fit is not None:
            fx0, fx1, ft0, ft1 = tick_fit
            if (abs(fx0 - axis.x_pixel_range[0]) > 2 or
                    abs(fx1 - axis.x_pixel_range[1]) > 2 or
                    abs(ft0 - axis.x_min) > 0.01 or
                    abs(ft1 - axis.x_max) > 0.01):
                print(f"[INFO] X轴刻度精拟合: "
                      f"px({axis.x_pixel_range[0]},{axis.x_pixel_range[1]}) "
                      f"{axis.x_min:.2f}~{axis.x_max:.2f}h -> "
                      f"px({fx0},{fx1}) {ft0:.2f}~{ft1:.2f}h")
                axis.x_pixel_range = (fx0, fx1)
                axis.x_min, axis.x_max = ft0, ft1

        # 识别单位
        for t in texts:
            if "元" in t["text"] or "MWh" in t["text"] or "价格" in t["text"]:
                axis.y_unit = t["text"]
            if "h" in t["text"] or "时" in t["text"] or "时间" in t["text"]:
                axis.x_unit = t["text"]

        n_good = len(x_ticks) + len(y_use)
        axis.confidence = min(1.0, n_good / 10.0)

        print(f"[INFO] 坐标轴标定: X=[{axis.x_min:.2f}, {axis.x_max:.2f}], "
              f"Y=[{axis.y_min:.2f}, {axis.y_max:.2f}]")
        print(f"[INFO] 像素映射: X像素={axis.x_pixel_range}, Y像素={axis.y_pixel_range}")

        return axis

    def _build_text_entries(self, ocr_lines: List, off_x: int, off_y: int) -> List[Dict]:
        """把OCR原始行解析为带绝对坐标的文本条目"""
        texts = []
        for line in ocr_lines or []:
            if not line:
                continue
            bbox, (text, score) = line
            abs_bbox = [[int(p[0]) + off_x, int(p[1]) + off_y] for p in bbox]
            center_x = sum(p[0] for p in abs_bbox) / 4
            center_y = sum(p[1] for p in abs_bbox) / 4
            texts.append({
                "text": text,
                "score": score,
                "bbox": abs_bbox,
                "center_x": center_x,
                "center_y": center_y,
                "is_number": self._is_number(text),
                "numeric_value": self._extract_number(text),
                "time_value": self._parse_time_label(text),
            })
        return texts

    def _parse_time_label(self, text: str) -> Optional[float]:
        """解析 'HH:MM' 时间标签为小时数（如 '20:15' -> 20.25），非时间格式返回None"""
        m = re.match(r'^\s*(\d{1,2})\s*[:：.]\s*(\d{2})\s*$', text)
        if not m:
            return None
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 24 and 0 <= mm < 60:
            return hh + mm / 60.0
        return None

    def _dedupe_ticks(self, ticks: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """刻度去重：同一数值只保留一次（OCR常重复识别同一刻度）"""
        seen = {}
        for p, v in sorted(ticks, key=lambda t: t[0]):
            if v not in seen:
                seen[v] = (p, v)
        return sorted(seen.values(), key=lambda t: t[0])

    def _fit_linear_map(self, pixels: List[float], values: List[float],
                        rounds: int = 2) -> Tuple[float, float]:
        """
        轴标定拟合 value = a*pixel + b。

        V3.7改为反向拟合 pixel = A*value + B 后再求逆：
        OCR识别出的刻度“数值”通常准确，误差主要在文字中心像素；
        正向最小二乘会把端点0/最大值当离群点剔除，导致负荷/出力整体抬高。
        带像素残差离群剔除，返回 (a, b)。
        """
        px = np.asarray(pixels, dtype=float)
        vv = np.asarray(values, dtype=float)
        if len(px) < 2:
            return 1.0, 0.0

        for _ in range(rounds):
            if len(px) < 4:
                break
            aa, bb = np.polyfit(vv, px, 1)  # pixel = aa*value + bb
            resid = np.abs(px - (aa * vv + bb))
            std = resid.std()
            if std < 1e-9:
                break
            # 文字中心本身可能有2~5px偏移；只有>8px才视为可疑离群
            keep = resid <= max(2.5 * std, 8.0)
            # 端点0/最大值对轴范围最关键，非极端错误(>20px)不剔除
            extreme = (vv == vv.min()) | (vv == vv.max())
            keep |= extreme & (resid <= 20.0)
            # 至少保留60%或3个刻度，避免端点0被连续误删
            if keep.all() or int(keep.sum()) < max(3, int(math.ceil(len(px) * 0.6))):
                break
            removed = len(px) - int(keep.sum())
            print(f"[INFO] 轴拟合剔除 {removed} 个离群刻度")
            px, vv = px[keep], vv[keep]

        aa, bb = np.polyfit(vv, px, 1)
        if abs(aa) < 1e-12:
            a, b = np.polyfit(px, vv, 1)
            return float(a), float(b)
        # value = (pixel - bb) / aa
        return float(1.0 / aa), float(-bb / aa)

    def _fit_time_map(self, pixels: List[float],
                      values: List[float]) -> Tuple[float, float]:
        """
        X轴时间刻度专用拟合（V4.3）：Theil-Sen中位数斜率。
        时间标签的“数值”是精确的（00:15/03:30...），误差全在OCR文字
        中心像素（±5px抖动）；最小二乘会被个别伪刻度/偏心标签拉偏，
        中位数斜率对一半以下的坏点免疫。返回 value = a*pixel + b。
        """
        px = np.asarray(pixels, dtype=float)
        vv = np.asarray(values, dtype=float)
        if len(px) < 2:
            return 1.0, 0.0
        slopes = []
        for i in range(len(px)):
            for j in range(i + 1, len(px)):
                dv = vv[j] - vv[i]
                if abs(dv) > 1e-9:
                    slopes.append((px[j] - px[i]) / dv)
        if not slopes:
            return 1.0, 0.0
        A = float(np.median(slopes))          # pixel = A*value + B
        if abs(A) < 1e-12:
            return 1.0, 0.0
        B = float(np.median(px - A * vv))
        return float(1.0 / A), float(-B / A)  # value = pixel/A - B/A

    def _is_number(self, text: str) -> bool:
        """判断文本是否为数字（支持负数、小数）"""
        cleaned = re.sub(r'[^\d\-.]', '', text)
        if not cleaned or cleaned == '-' or cleaned == '.':
            return False
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        # 尝试匹配各种数字格式
        patterns = [
            r'(-?\d+\.?\d*)',           # 普通数字
            r'(-?\d{1,3}(?:,\d{3})+\.?\d*)',  # 千分位
        ]
        for pattern in patterns:
            match = re.search(pattern, text.replace(',', ''))
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _dump_ocr_debug(self, output_dir: str, base_name: str) -> str:
        """把OCR识别的全部文本及坐标落盘，用于人工核对刻度识别是否正确"""
        path = os.path.join(output_dir, f"{base_name}_ocr_debug.txt")
        texts = getattr(self, "text_data", [])
        with open(path, "w", encoding="utf-8") as f:
            f.write("text\tscore\tcenter_x\tcenter_y\tnumeric\ttime_value\n")
            for t in texts:
                f.write(f"{t['text']}\t{t['score']:.3f}\t{t['center_x']:.0f}\t"
                        f"{t['center_y']:.0f}\t{t['numeric_value']}\t"
                        f"{t.get('time_value')}\n")
        print(f"[INFO] OCR调试文本已保存: {path} (共{len(texts)}条)")
        return path

    # --------------------------------------------------------------------------
    # 步骤4: 曲线自动追踪
    # --------------------------------------------------------------------------
    def extract_curves(self, img: np.ndarray, roi: Tuple[int, int, int, int], 
                      axis: AxisInfo) -> List[CurveData]:
        """
        自动追踪并提取ROI区域内的所有曲线

        策略：
        1. 在ROI内去除网格线和坐标轴
        2. 按颜色聚类分离多条曲线
        3. 对每条曲线进行像素追踪
        4. 像素坐标→实际数值转换
        """
        x, y, w, h = roi
        roi_img = img[y:y+h, x:x+w]
        self._last_axis = axis  # 供插值阶段裁剪越界值
        # 曲线像素点是裁剪图相对坐标，而坐标轴像素范围是全图绝对坐标，
        # _pixel_to_real 映射时必须加上本偏移（多面板模式关键！）
        self._px_offset = (x, y)

        curves = []

        # 方法1: 基于颜色分离（适用于彩色曲线图）
        color_curves = self._extract_by_color(roi_img, axis)
        curves.extend(color_curves)

        # 方法2: 如果颜色方法未找到足够曲线，使用边缘检测
        if len(curves) < 1:
            edge_curves = self._extract_by_edge(roi_img, axis)
            curves.extend(edge_curves)

        # 方法3: 基于亮度/对比度的通用曲线检测
        if len(curves) < 1:
            generic_curves = self._extract_generic(roi_img, axis)
            curves.extend(generic_curves)

        # ==================== 后处理：过滤 + 去重 + 限量 ====================
        curves = self._filter_and_dedupe_curves(curves, axis)

        # 为曲线命名
        for i, curve in enumerate(curves):
            if not curve.name:
                curve.name = f"曲线_{i+1}"

        print(f"[INFO] 共提取 {len(curves)} 条有效曲线")
        return curves

    def _repair_y_ticks(self, y_use: List[Tuple[float, float]],
                        texts: List[Dict], x: int, w: int
                        ) -> Optional[List[Tuple[float, float]]]:
        """V4.7：补回与峰值标注粘连而被位置/数值过滤误剔除的Y轴刻度。

        粘连文本（如"12,00730.09"=刻度"12,000"+蓝色标注"10730.09"）
        数值不可用、中心X右移被剔除，但其像素行仍落在主导等差数列上；
        按数列重新赋值补回。风电面板曾因此丢失顶（12,000）/底（0）
        刻度，Y轴被错标成2035~10027（真值0~12000），晚间近0的实时
        出力被钳成2035平线、白天数值整体压缩。
        防护：行须与数列对齐(±25%间隔)、不与现有刻度行/值冲突、
        外扩≤1.5个间隔——绘图区内的峰值标注中心X通常>w*0.2被排除。"""
        if len(y_use) < 2:
            return None
        vv = sorted(set(float(v) for _, v in y_use))
        diffs = [vv[i + 1] - vv[i] for i in range(len(vv) - 1)
                 if vv[i + 1] - vv[i] > 1e-9]
        if not diffs:
            return None
        interval = float(np.median(diffs))
        a, b = self._fit_linear_map([p for p, _ in y_use],
                                    [v for _, v in y_use])
        if abs(a) < 1e-9 or interval <= 0:
            return None
        lo, hi = min(vv), max(vv)
        rows_used = [float(p) for p, _ in y_use]
        out = list(y_use)
        added = 0
        for t in texts:
            if t.get("numeric_value") is None:
                continue
            if not (x - 30 <= t["center_x"] <= x + w * 0.2):
                continue
            row = float(t["center_y"])
            if any(abs(row - r0) < 8 for r0 in rows_used):
                continue                      # 已有刻度的行
            v_pred = a * row + b
            v_new = round(v_pred / interval) * interval
            if abs(v_new - v_pred) > interval * 0.25:
                continue                      # 行不对齐等差数列
            if v_new < lo - 1.5 * interval or v_new > hi + 1.5 * interval:
                continue                      # 外扩不超过1.5个间隔
            if any(abs(v_new - v0) < interval * 0.01 for _, v0 in out):
                continue                      # 该值已存在
            out.append((row, v_new))
            rows_used.append(row)
            added += 1
        if not added:
            return None
        out = self._dedupe_ticks(out)
        print(f"[INFO] Y刻度修复: 补回{added}个粘连刻度，值域 -> "
              f"{min(v for _, v in out):.0f}~{max(v for _, v in out):.0f}")
        return out

    # OCR形近数字替换组（无衬线印刷体常见误读：6/0/8、1/2/7、5/6/8等）
    _OCR_DIGIT_CONFUSE = {
        '0': '68', '6': '08', '8': '06',
        '1': '27', '2': '17', '7': '12',
        '5': '68', '3': '58', '9': '45', '4': '9',
    }

    def _repair_ocr_number(self, v: float, gmax: float,
                           fire_err: float = 0.08,
                           accept_err: float = 0.03) -> Optional[Tuple[float, float]]:
        """V4.9 数字级OCR纠错：峰值标注被误读时（如26960.82->20960.81，
        与曲线像素峰值差27%），用曲线稳健峰值（P98）作独立量测，
        对数值每位数字尝试形近替换（最多2位，组合数可控），按“替换
        最少->误差最小”选最优。
        三重门控防误纠：
          1) 原值与P98偏差<=fire_err(8%)不触碰——正确识别零影响
             （太阳能15066.57对P98仅3.2%，圆点假锚18234不得作证）；
          2) 修正值与P98误差<=accept_err(3%)才采纳；
          3) P98对单点/窄峰污染免疫（假圆点、标注文字骑线均为窄峰）。
        整数部分不允许前导零。"""
        if v is None or gmax is None or abs(gmax) < 1e-6:
            return None
        if abs(v - gmax) / abs(gmax) <= fire_err:
            return None
        s = f"{float(v):.2f}"
        neg = s.startswith('-')
        if neg:
            s = s[1:]
        dot = s.index('.')
        base_digits = list(s.replace('.', ''))
        n = len(base_digits)

        def rebuild(ds):
            int_part = ''.join(ds[:dot])
            if len(int_part) > 1 and int_part[0] == '0':
                return None
            try:
                return float(('-' if neg else '') + int_part +
                             '.' + ''.join(ds[dot:]))
            except (ValueError, IndexError):
                return None

        def variants(pos_combo):
            """对pos_combo中的位置做形近替换，产出(新数字串, 替换数)"""
            results = []
            def rec(idx, ds):
                if idx == len(pos_combo):
                    nv = rebuild(ds)
                    if nv is not None and nv != v:
                        results.append(nv)
                    return
                p = pos_combo[idx]
                orig = ds[p]
                for nd in self._OCR_DIGIT_CONFUSE.get(orig, ''):
                    ds[p] = nd
                    rec(idx + 1, ds)
                ds[p] = orig
            rec(0, list(base_digits))
            return results

        best = None          # (替换数, 误差, 值)
        g = abs(gmax)
        for nsub, combos in ((1, [(i,) for i in range(n)]),
                             (2, [(i, j) for i in range(n)
                                  for j in range(i + 1, n)])):
            for combo in combos:
                for nv in variants(combo):
                    err = abs(nv - gmax) / g
                    if err <= accept_err:
                        key = (nsub, err)
                        if best is None or key < best[0]:
                            best = (key, err, nv)
            if best is not None:
                break        # 单替换已命中，不再做双替换（最大似然）
        if best is None:
            return None
        return best[2], best[1]

    def _filter_and_dedupe_curves(self, curves: List[CurveData],
                                  axis: Optional[AxisInfo] = None,
                                  max_curves: int = 8) -> List[CurveData]:
        """
        过滤无效曲线并去除重复：
        1. 剔除数值范围异常（文字/图例被误识别为曲线的情况）
        2. 合并像素轨迹几乎重合的曲线（边缘检测常把一条线识别成两条）
        3. 按像素点数排序，最多保留 max_curves 条
        """
        if axis is not None and axis.y_max > axis.y_min:
            # 以坐标轴标定范围为基准，上下各放宽30%
            span = axis.y_max - axis.y_min
            v_max = axis.y_max + 0.3 * span
            v_min = axis.y_min - 0.3 * span
        else:
            val_cfg = self.config["validation"]
            v_max = val_cfg["max_price"] * 1.5
            v_min = val_cfg["min_price"] * 1.5

        # 1. 范围过滤 + 按像素点数降序
        candidates = []
        for c in curves:
            ys = [p[1] for p in c.points]
            if not ys:
                continue
            if max(ys) > v_max or min(ys) < v_min:
                print(f"[INFO] 剔除超范围曲线 {c.name}: "
                      f"[{min(ys):.1f}, {max(ys):.1f}]")
                continue
            candidates.append(c)
        candidates.sort(key=lambda c: len(c.pixel_points), reverse=True)

        # 2. 轨迹重合去重（不同颜色的曲线不可能是重复，直接跳过比较）
        kept = []
        for c in candidates:
            dup = False
            for k in kept:
                if (c.color_name != k.color_name
                        and c.color_name != "unknown" and k.color_name != "unknown"):
                    continue
                if self._curves_pixel_distance(c, k) < 8.0:
                    print(f"[INFO] 合并重复曲线 {c.name}（与 {k.name} 轨迹重合）")
                    dup = True
                    break
            if not dup:
                kept.append(c)
            if len(kept) >= max_curves:
                break
        return kept

    def _curves_pixel_distance(self, c1: CurveData, c2: CurveData) -> float:
        """两条曲线在共同X列上的平均纵向像素距离（越小越相似）"""
        d1 = {x: y for x, y in c1.pixel_points}
        d2 = {x: y for x, y in c2.pixel_points}
        common = set(d1) & set(d2)
        if len(common) < 30:
            return 1e9  # 重叠太少，视为不同曲线
        return float(np.mean([abs(d1[px] - d2[px]) for px in common]))

    def _extract_by_color(self, roi_img: np.ndarray, axis: AxisInfo) -> List[CurveData]:
        """基于HSV色相提取曲线（V3：匹配Dashboard真实配色，S/V阈值排除灰白黑）"""
        curves = []
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        roi_w = roi_img.shape[1]
        # V4.6b：留存开运算前原始掩码（按颜色），供_mask_to_curve碎片接续
        # 延伸使用——2px细线会被3x3开运算整体腐蚀（全网发电预测出力上午
        # 段因此全丢、被钳成峰值直线）
        self._raw_color_masks = {}

        for color_name, ranges in HSV_CURVE_COLORS.items():
            # 合并该颜色的所有色相区间
            mask = None
            for lo, hi in ranges:
                m = cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                                np.array(hi, dtype=np.uint8))
                mask = m if mask is None else cv2.bitwise_or(mask, m)
            self._raw_color_masks[color_name] = mask

            # 形态学操作去噪
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # 提取曲线点
            curve = self._mask_to_curve(mask, axis, color_name)
            if curve is None:
                continue
            if len(curve.pixel_points) <= self.config["chart"]["min_curve_points"]:
                continue
            # 曲线必须横跨"绘图区"宽度的25%以上（排除图例色块/局部文字）
            # 注意：按坐标轴标定的绘图区宽度计算，而不是ROI全宽——
            # 太阳能等只有白天有数据的曲线天然只占绘图区40%左右，
            # 按ROI全宽35%会被误杀
            plot_w = abs(axis.x_pixel_range[1] - axis.x_pixel_range[0])
            xs = [p[0] for p in curve.pixel_points]
            if max(xs) - min(xs) < plot_w * 0.25:
                print(f"[INFO] 剔除短跨度曲线 {color_name}: "
                      f"跨度{max(xs)-min(xs)}px < 绘图区25%({plot_w*0.25:.0f}px)")
                continue
            curves.append(curve)

        return curves

    def _extract_load_tooltip_anchors(self, texts: List[Dict],
                                      rect: Tuple[int, int, int, int]) -> Dict:
        """提取负荷tooltip中的精确锚点：时间及四条负荷数值。"""
        x, y, w, h = rect
        inner = [t for t in texts
                 if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h]
        inner.sort(key=lambda t: (t["center_y"], t["center_x"]))

        def _num_parts(txt: str) -> List[str]:
            return re.findall(r'\d[\d,]*\.?\d*', txt.replace('，', ','))

        def _combine_parts(parts: List[str]) -> Optional[float]:
            if not parts:
                return None
            raw = ''.join(p.replace(',', '') for p in parts).strip()
            if not raw:
                return None
            try:
                # 多个小数点说明是“82. + 446.01”这类碎片，只保留最后一个小数点
                if raw.count('.') > 1:
                    head, tail = raw.rsplit('.', 1)
                    raw = head.replace('.', '') + '.' + tail
                return float(raw)
            except Exception:
                return None

        def _parse_full_number(raw_txt: str) -> Optional[float]:
            """V4.3：优先按完整千分位数字解析原文。
            '40,347.87'->40347.87、'82,446.01'->82446.01、'79,000'->79000；
            OCR逗号误读为点的真实形态（PaddleOCR实测）：
            '40.347.87'->40347.87、'82.446'->82446、'79.000'->79000。
            找不到完整形态才返回None。"""
            s = raw_txt.replace('，', ',').replace(' ', '')
            # 广义千分位：千位头 + 三位节 + 小数，分隔符逗号/点均可
            m = re.search(r'(?<![\d.,])(\d{1,3})[.,](\d{3})[.,](\d{1,2})(?![\d.,])', s)
            if m:
                return (int(m.group(1)) * 1000 + int(m.group(2)) +
                        float('0.' + m.group(3)))
            # 仅千位头 + 三位节（'79,000' / '79.000' / '82.446'）
            m = re.search(r'(?<![\d.,])(\d{1,3})[.,](\d{3})(?![\d.,])', s)
            if m:
                return float(int(m.group(1)) * 1000 + int(m.group(2)))
            return None

        def _join_value_parts(head_txt: str, tail_txt: str) -> List[float]:
            """V4.3：拼接拆分碎片。
            '40'+'347.87'->40347.87；'82'+'446.01'->82446.01；
            '79'+'000'->79000；'82.446'+'01'->82446.01。"""
            h = re.sub(r'[^\d.]', '', head_txt.replace(',', ''))
            t = re.sub(r'[^\d.]', '', tail_txt.replace(',', ''))
            out = []
            if re.fullmatch(r'\d{1,3}', h or ''):
                m = re.fullmatch(r'(\d{1,3})(?:\.(\d{1,2}))?', t or '')
                if m:
                    base = int(h) * 1000 + int(m.group(1))
                    if m.group(2):
                        base += float('0.' + m.group(2))
                    out.append(float(base))
            m = re.fullmatch(r'(\d{1,3})\.(\d{3})', h or '')
            if m:
                base = float(int(m.group(1)) * 1000 + int(m.group(2)))
                out.append(base)
                if re.fullmatch(r'\d{1,2}', t or ''):
                    out.append(base + float('0.' + t))
            return [v for v in out if 1000 <= v <= 150000]

        def _normalize_value(v: Optional[float], raw_txt: str) -> Optional[float]:
            """V4.3：完整千分位直接解析优先；绝不盲目×1000。"""
            full = _parse_full_number(raw_txt)
            if full is not None and 1000 <= full <= 150000:
                return full
            parts = _num_parts(raw_txt)
            combined = _combine_parts(parts[-2:]) if len(parts) >= 2 else None
            if combined is not None and 1000 <= combined <= 150000:
                return combined
            if v is None and parts:
                try:
                    v = float(parts[-1].replace(',', ''))
                except Exception:
                    v = None
            if v is None:
                return None
            return float(v)

        # ---- 1) 时间：优先完整11:15；其次“11:预测...”+附近15；最后交给竖线兜底 ----
        tooltip_time = None
        hour_only = None
        for t in inner:
            if t["center_y"] > y + h * 0.45:
                continue
            txt = t["text"]
            # V4.3：结尾\b在Unicode汉字(测)前失效，改用(?!\d)；
            # 真实OCR'11:15测/实际负荷及出力'曾被误判为15.0
            m = re.search(r'(?<!\d)([01]?\d|2[0-3])\s*[:：]\s*([0-5]\d)(?!\d)', txt)
            if m:
                tooltip_time = int(m.group(1)) + int(m.group(2)) / 60.0
                break
            mh = re.search(r'(?<!\d)([01]?\d|2[0-3])\s*[:：]?\s*(?:测/实际|预测/实际|实际负荷)', txt)
            if mh and hour_only is None:
                hour_only = int(mh.group(1))
                # 同一行附近找单独的15/30/45分钟碎片
                for nt in inner:
                    if abs(nt["center_y"] - t["center_y"]) > 24:
                        continue
                    if nt.get("numeric_value") in (0, 15, 30, 45):
                        tooltip_time = hour_only + float(nt["numeric_value"]) / 60.0
                        break
        if tooltip_time is None and hour_only is not None:
            tooltip_time = float(hour_only)  # 后续_process_panel用蓝色竖线精化

        mapping = {"预测直调负荷": "预测直调负荷",
                   "实际直调负荷": "实际直调负荷",
                   "预测全网负荷": "预测全网负荷",
                   "实际全网负荷": "实际全网负荷"}
        values = {}

        # ---- 2) 数值提取：完整千分位直读 + 碎片拼接（V4.3重写） ----
        # 真实故障形态（V4.2日志）：OCR把"预测直调负荷: 40,347.87"拆成
        # "预测直调负荷: 40" + "347.87"，旧逻辑先落值40再×1000成40000；
        # "82,446.01"被读成"82.446"丢小数成82446.0。新逻辑：
        # 可疑千位头（40/82.446）绝不直接落值，必须与右侧/下一行碎片拼接。
        numeric_items = [t for t in inner if _num_parts(t["text"]) or
                         t.get("numeric_value") is not None]

        def _collect_for_label(label) -> Optional[float]:
            txt = label["text"]
            candidates = []  # (score, value)：分低者优
            txt_clean = txt.replace('，', ',')
            tail_m = re.search(r'(\d[\d,]*\.?\d*)\s*$', txt_clean)
            head_txt = ""
            suspicious_tail = False
            if tail_m:
                head_txt = tail_m.group(1)
                # 1~3位裸整数(40/79) 或 小数点误读千分节(82.446) = 可疑千位头
                if re.fullmatch(r'\d{1,3}', head_txt) or \
                        re.fullmatch(r'\d{1,3}\.\d{3}', head_txt):
                    suspicious_tail = True
            # a) 同条文本完整数字（40,347.87 -> 40347.87）
            v = _normalize_value(label.get("numeric_value"), txt)
            if v is not None and v >= 1000 and not suspicious_tail:
                candidates.append((0.0, v))
            # 收集标签右侧同行/下一行数字碎片
            frags = []  # (row_rank, dx, dy, item)
            for nt in numeric_items:
                if nt is label:
                    continue
                dx = nt["center_x"] - label["center_x"]
                dy = nt["center_y"] - label["center_y"]
                if abs(dy) <= 26 and -30 <= dx <= 420:
                    frags.append((0, dx, dy, nt))
                elif 0 < dy <= 46 and abs(dx) <= 220:
                    frags.append((1, dx, dy, nt))
            frags.sort(key=lambda f: (f[0], abs(f[2]), max(f[1], 0)))
            for row_rank, dx, dy, nt in frags:
                # d) 单碎片完整数字（79,000 -> 79000）
                vf = _normalize_value(nt.get("numeric_value"), nt["text"])
                if vf is not None and vf >= 1000:
                    candidates.append((10 + row_rank * 5 + abs(dy) * 0.2 +
                                       max(dx, 0) * 0.02, vf))
                # b) 标签千位头 + 碎片（40+347.87 / 82.446+01）
                if head_txt:
                    for vj in _join_value_parts(head_txt, nt["text"]):
                        candidates.append((2.0 + row_rank + abs(dy) * 0.1, vj))
            # c) 相邻同行碎片互拼（82 + 446.01）
            same_row_frags = [f for f in frags if f[0] == 0]
            for i in range(len(same_row_frags) - 1):
                t1 = same_row_frags[i][3]["text"]
                t2 = same_row_frags[i + 1][3]["text"]
                for vj in _join_value_parts(t1, t2):
                    candidates.append((4.0 + i, vj))
            if not candidates:
                return None
            # 整数值（如82446.0）说明小数可能丢失，同分时让带小数值优先
            candidates = [(s + (0.05 if float(v) == int(v) else 0.0), v)
                          for s, v in candidates]
            full = [(s, v) for s, v in candidates if 10000 <= v <= 120000]
            pool = full or [(s, v) for s, v in candidates if v >= 1000]
            if not pool:
                return None
            return min(pool, key=lambda item: item[0])[1]

        for label in inner:
            txt = label["text"]
            if label["center_y"] > y + h * 0.50:
                continue
            has_colon = (":" in txt or "：" in txt)
            for key, col in mapping.items():
                if key not in txt or col in values:
                    continue
                if not has_colon and label["center_x"] > x + w * 0.60:
                    continue
                v = _collect_for_label(label)
                if v is not None and 0 <= v <= 150000:
                    values[col] = v

        # V4.3：已删除“40.0=>40000”式×1000盲兜底——
        # 完整值必须由千分位直读或碎片拼接得出，缺失就留空交由曲线值。

        if values:
            print(f"[INFO] 负荷tooltip锚点识别: {values} @ {tooltip_time}")
        return {"time": tooltip_time, "values": values}

    def _snap_load_tooltip_anchors(self, curves: List[CurveData], anchor: Dict):
        """用tooltip精确值整体微校正并强制写入对应15分钟时点。"""
        t_anchor = anchor.get("time")
        values = anchor.get("values", {})
        if t_anchor is None or not values:
            return
        for curve in curves:
            target = values.get(curve.name)
            if target is None or not curve.points:
                continue
            xs = [p[0] for p in curve.points]
            ys = [p[1] for p in curve.points]
            idx = min(range(len(xs)), key=lambda i: abs(xs[i] - t_anchor))
            current = ys[idx]
            # 轴标定仍可有少量线性误差：比例在±1.5%内时整体缩放，再写入精确锚点
            # V4.4：阈值20%->5%->1.5%。视觉轴+hover双锚点标定已达像素级，
            # 真实系统偏差<1%；而tooltip锚点位于圆环畸变区(±13px)，该处
            # 读数经插值桥接仍有~1%非线性误差。>1.5%的“偏差”几乎必然是
            # 局部污染(圆环/线顶/虚线粘连)，整体缩放会把局部误差放大成
            # 全天系统偏差——实测1.4%的锚点误读曾把全天压低~860MW。
            if abs(current) > 1e-6:
                ratio = target / current
                if 0.985 <= ratio <= 1.015:
                    ys = [v * ratio for v in ys]
                else:
                    print(f"[WARN] 负荷锚点{curve.name}偏差{abs(ratio-1):.1%}>1.5%，"
                          f"仅写锚点不做整体缩放(提取值{current:.0f}疑似局部污染)")
            ys[idx] = target
            curve.points = [(xx, yy) for xx, yy in zip(xs, ys)]
            curve._peak_snapped_value = float(target)
            curve._peak_snapped_time = float(xs[idx])
            curve._peak_guard_cap = False  # tooltip锚点不是全天最大值，不能封顶
            print(f"[INFO] 负荷tooltip锚点: {curve.name} -> {target:.2f} @ "
                  f"{xs[idx]:.2f}h")

    def _load_curves_degenerate(self, curves: List[CurveData], axis: AxisInfo) -> bool:
        """识别四条负荷曲线退化为常数/同一点的情况。"""
        if len(curves) < 4:
            return True
        ranges = []
        means = []
        for c in curves:
            ys = np.array([p[1] for p in c.points], dtype=float)
            if len(ys) < 2:
                return True
            # V4.0：唯一值过少也说明提取来自边框/图例/单一直线
            if len(set(np.round(ys, 2).tolist())) < 5:
                return True
            ranges.append(float(ys.max() - ys.min()))
            means.append(float(ys.mean()))
        span = max(axis.y_max - axis.y_min, 1.0)
        all_flat = max(ranges) < span * 0.03
        same_value = (max(means) - min(means)) < span * 0.01
        return bool(all_flat or (same_value and max(ranges) < span * 0.10))

    def _detect_load_axis_visual(self, img: np.ndarray,
                                 rect: Tuple[int, int, int, int],
                                 legend_boxes: Optional[List] = None,
                                 ocr_axis: Optional[AxisInfo] = None) -> Optional[AxisInfo]:
        """
        负荷面板视觉轴标定：不依赖OCR刻度文字。

        依据Dashboard固定结构：
        - 底部蓝色X轴对应0 MW，端点对应00:15和23:00；
        - 顶部第一条浅灰网格线对应100,000 MW；
        - tooltip可能遮挡标题和Y轴文字，因此轴范围必须直接从像素几何恢复。
        """
        x, y, w, h = rect
        roi = img[y:y + h, x:x + w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([92, 45, 80]), np.array([125, 255, 255]))

        # 1) 底部X轴：下半幅面中蓝色横跨最长的一行
        row_scores = (blue > 0).sum(axis=1)
        row_candidates = [(int(s), yy) for yy, s in enumerate(row_scores)
                          if yy >= h * 0.55 and s > max(40, w * 0.25)]
        if not row_candidates:
            return None
        _, yb_rel = max(row_candidates)

        # 2) X轴端点：在轴线±2px蓝色投影中取最长连续段
        band = blue[max(0, yb_rel - 2):min(h, yb_rel + 3), :]
        col_has = (band > 0).any(axis=0)
        runs, start = [], None
        for xx, ok in enumerate(col_has):
            if ok and start is None:
                start = xx
            if start is not None and (not ok or xx == len(col_has) - 1):
                end = xx - 1 if not ok else xx
                runs.append((start, end, end - start + 1))
                start = None
        if not runs:
            return None
        x0_rel, x1_rel, run_len = max(runs, key=lambda r: r[2])
        if run_len < max(120, w * 0.30):
            return None

        # 3) 顶部100000网格线：从图例下方开始收集浅灰水平线，
        # 先按相邻行聚类，再排除“绘图区顶边框/legend分隔线”。
        if legend_boxes:
            legend_bottom = max(max(p[1] for p in bb) for bb in legend_boxes) - y
            y_start = max(legend_bottom + 3, int(h * 0.28))
        else:
            legend_bottom = int(h * 0.25)
            y_start = int(h * 0.28)
        # 扫描到X轴前5px，保留20,000网格线用于等距序列验证
        y_end = max(y_start + 5, yb_rel - 5)
        line_scores = []
        for yy in range(max(0, y_start), min(h, y_end)):
            row = roi[yy, x0_rel:x1_rel + 1].astype(np.int16)
            mean = row.mean(axis=1)
            span = row.max(axis=1) - row.min(axis=1)
            neutral = (span < 12) & (mean > 145) & (mean < 250)
            score = int(neutral.sum())
            if score > max(20, (x1_rel - x0_rel + 1) * 0.08):
                line_scores.append((score, yy))
        if not line_scores:
            return None

        # 相邻1~2行通常是同一条线，聚类后以最大分为簇分数
        clusters = []
        for score, yy in line_scores:
            if not clusters or yy - clusters[-1]["rows"][-1] > 2:
                clusters.append({"rows": [yy], "scores": [score]})
            else:
                clusters[-1]["rows"].append(yy)
                clusters[-1]["scores"].append(score)
        line_clusters = []
        for cl in clusters:
            best_i = int(np.argmax(cl["scores"]))
            center = float(np.average(cl["rows"], weights=cl["scores"]))
            line_clusters.append({"y": cl["rows"][best_i], "center": center,
                                  "score": max(cl["scores"])})

        # 3a) OCR轴若与视觉X轴底部一致，则优先选最接近100000刻度文字的线
        yt_rel = None
        if ocr_axis is not None:
            ocr_yb = max(ocr_axis.y_pixel_range) - y
            ocr_yt = min(ocr_axis.y_pixel_range) - y
            ocr_valid = (90000 <= ocr_axis.y_max <= 110000 and
                         -5000 <= ocr_axis.y_min <= 5000 and
                         abs(ocr_yb - yb_rel) <= 8)
            if ocr_valid:
                near = [c for c in line_clusters if abs(c["center"] - ocr_yt) <= 30]
                if near:
                    yt_rel = min(near, key=lambda c: abs(c["center"] - ocr_yt))["y"]

        # 3b) 无可靠OCR时，用0~100000轴的5等分网格序列评分。
        # 不能简单跳过legend下第一条线：完整Dashboard中第一条线本身就是
        # 100000网格线(1078)，而80/60/40/20网格线与其等距；裁剪小图中的
        # 第一条线则可能是绘图区顶边框。序列证据比位置规则可靠。
        if yt_rel is None:
            best_candidate = None
            best_score = -1.0
            best_matched = 0
            for top in line_clusters:
                if yb_rel - top["center"] < 80:
                    continue
                spacing = (yb_rel - top["center"]) / 5.0
                if spacing < 12:
                    continue
                tol = max(3.0, spacing * 0.18)
                seq_score = top["score"] * 0.20
                matched = 0
                for k in range(1, 5):  # 80000/60000/40000/20000
                    expected = top["center"] + spacing * k
                    near = [c for c in line_clusters
                            if abs(c["center"] - expected) <= tol]
                    if near:
                        nb = max(near, key=lambda c: c["score"] /
                                 (1.0 + abs(c["center"] - expected)))
                        dist = abs(nb["center"] - expected)
                        seq_score += nb["score"] / (1.0 + dist)
                        matched += 1
                seq_score *= (1.0 + matched * 0.75)
                if seq_score > best_score:
                    best_score = seq_score
                    best_candidate = top
                    best_matched = matched
            if best_candidate is None:
                return None
            yt_rel = best_candidate["y"]
            print(f"[DEBUG] 负荷网格序列: top={y + yt_rel}, 匹配{best_matched}/4条, "
                  f"得分={best_score:.1f}")

        if yb_rel - yt_rel < 80:
            return None

        axis = AxisInfo(x_min=0.25, x_max=23.0,
                        y_min=0.0, y_max=100000.0,
                        x_pixel_range=(x + x0_rel, x + x1_rel),
                        y_pixel_range=(y + yt_rel, y + yb_rel))
        print(f"[INFO] 负荷视觉轴: X=({x + x0_rel},{x + x1_rel}), "
              f"Y=({y + yt_rel},{y + yb_rel}), 0~100000")
        return axis

    def _refine_load_tooltip_time_by_ocr(self, img: np.ndarray,
                                         rect: Tuple[int, int, int, int]) -> Optional[float]:
        """可选Tesseract定点复核tooltip标题时间（如11:15被Paddle漏读）。"""
        try:
            import pytesseract  # type: ignore
        except Exception:
            return None
        x, y, w, h = rect
        # tooltip标题通常位于面板左上1/4区域
        x0 = max(0, x + int(w * 0.01))
        y0 = max(0, y + int(h * 0.01))
        x1 = min(img.shape[1], x + int(w * 0.72))
        y1 = min(img.shape[0], y + int(h * 0.22))
        if x1 <= x0 or y1 <= y0:
            return None
        crop = img[y0:y1, x0:x1]
        crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        for psm in (11, 12, 6):
            try:
                txt = pytesseract.image_to_string(crop, lang="eng",
                                                  config=f"--psm {psm}")
            except Exception:
                continue
            m = re.search(r'\b([01]?\d|2[0-3])\s*[:：]\s*([0-5]\d)\b', txt)
            if m:
                t_val = int(m.group(1)) + int(m.group(2)) / 60.0
                print(f"[INFO] 负荷tooltip时间Tesseract复核: {t_val:.2f}h")
                return float(t_val)
        return None

    def _detect_load_hover_line_x(self, img: np.ndarray,
                                  rect: Tuple[int, int, int, int],
                                  axis: AxisInfo) -> Optional[int]:
        """检测tooltip蓝色竖线中心的绝对x像素（纯像素量测，不依赖轴换算）。"""
        if axis is None:
            return None
        x, y, w, h = rect
        roi = img[y:y + h, x:x + w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([92, 45, 80]), np.array([125, 255, 255]))
        y0, y1 = sorted(axis.y_pixel_range)
        x0, x1 = sorted(axis.x_pixel_range)
        ry0, ry1 = max(0, y0 - y), min(h, y1 - y)
        rx0, rx1 = max(0, x0 - x), min(w, x1 - x)
        if ry1 <= ry0 or rx1 <= rx0:
            return None
        # 排除底部X轴，只统计绘图区上部95%
        span_y = ry1 - ry0
        region = blue[ry0:ry1 - max(2, int(span_y * 0.05)), rx0:rx1]
        scores = (region > 0).sum(axis=0)
        if len(scores) == 0 or scores.max() < max(15, span_y * 0.25):
            return None
        return x + int(np.argmax(scores)) + rx0

    def _detect_load_hover_time(self, img: np.ndarray,
                                rect: Tuple[int, int, int, int],
                                axis: AxisInfo) -> Optional[float]:
        """tooltip时间OCR缺失时，用蓝色竖线中心推断并吸附到15分钟。"""
        if axis is None:
            return None
        hover_x = self._detect_load_hover_line_x(img, rect, axis)
        if hover_x is None:
            return None
        x, y, w, h = rect
        y0, _ = sorted(axis.y_pixel_range)
        self._px_offset = (x, y)
        try:
            t_val, _ = self._pixel_to_real(
                [(hover_x - x, max(0, y0 - y) + 2)], axis)[0]
        except Exception:
            return None
        snapped = round(t_val * 4) / 4.0
        print(f"[INFO] 负荷tooltip时间竖线兜底: {t_val:.2f}h -> {snapped:.2f}h")
        return float(snapped)

    def _fit_load_x_axis_by_ticks(self, img: np.ndarray,
                                  rect: Tuple[int, int, int, int],
                                  axis: AxisInfo,
                                  texts: List[Dict]) -> Optional[Tuple[int, int]]:
        """V4.4：用X轴刻度标签连通域拟合 px=a*t+b（像素级精确）。

        蓝线端点含留白（右端实测延出13~26px），hover双锚点受左端点
        1~3px小留白影响仍有±5px误差；刻度标签中心与时刻一一对应，
        连通域拟合残差<±0.5px，是最精确的X标定。标签数与OCR解析出的
        时刻数不一致时返回None（交给hover锚点兜底）。"""
        x0_line, x1_line = sorted(axis.x_pixel_range)
        yb = max(axis.y_pixel_range)
        # 1) 刻度时刻：OCR文本中轴下方、与轴x重叠的HH:MM（合并标签串
        # 如"03:3006:45"也能被finditer逐个切出）
        times = []
        for t in texts:
            if not (yb + 2 <= t["center_y"] <= yb + 60):
                continue
            if t["center_x"] < x0_line - 80 or t["center_x"] > x1_line + 80:
                continue
            for m in re.finditer(r'([01]?\d|2[0-3])\s*[:：]\s*([0-5]\d)',
                                 t["text"]):
                hh, mm = int(m.group(1)), int(m.group(2))
                if mm < 60:
                    times.append(hh + mm / 60.0)
        times = sorted(set(times))
        if len(times) < 4:
            return None
        # 2) 标签带连通域：轴下方4~32px，灰字阈值200，列投影聚簇
        band_y0, band_y1 = yb + 4, min(img.shape[0], yb + 32)
        off = max(0, x0_line - 40)
        band = cv2.cvtColor(img[band_y0:band_y1, off:x1_line + 40],
                            cv2.COLOR_BGR2GRAY)
        text_mask = (band < 200).astype(np.uint8)
        colhas = (text_mask > 0).sum(axis=0)
        groups = []
        for i, v in enumerate(colhas):
            if v > 0:
                if not groups or i - groups[-1][1] > 10:
                    groups.append([i, i])
                else:
                    groups[-1][1] = i
        centers = [(a + b) / 2.0 + off for a, b in groups if b - a >= 6]
        # 剔除轴左侧的Y轴"0"标签（其中心在x0-8以左）
        centers = [c for c in centers if c >= x0_line - 8]
        if len(centers) != len(times) or len(centers) < 4:
            return None
        A = np.polyfit(times, centers, 1)
        # V4.7：端点直接取极值时刻的拟合像素，不再依赖axis.x_min/x_max
        # （OCR合并标签串按字符位置估算有系统偏差，风电曾x_min=1.333
        # 偏移+1.08h）；返回极值时刻供调用方一并校正x_min/x_max。
        t0, t1 = times[0], times[-1]
        fx0 = A[0] * t0 + A[1]
        fx1 = A[0] * t1 + A[1]
        slope_line = (x1_line - x0_line) / max(axis.x_max - axis.x_min, 1e-9)
        # 3) 合理性：端点与蓝线偏差有限、斜率与蓝线斜率相差<15%
        if (abs(fx0 - x0_line) > 12 or abs(fx1 - x1_line) > 40 or
                abs(A[0] - slope_line) > slope_line * 0.15):
            return None
        return (int(round(fx0)), int(round(fx1)), t0, t1)

    def _refine_load_x_axis_by_hover(self, img: np.ndarray,
                                     rect: Tuple[int, int, int, int],
                                     axis: AxisInfo,
                                     texts: List[Dict]) -> AxisInfo:
        """V4.4：hover蓝色竖线x像素+tooltip时间双锚点修正X映射。

        蓝色X轴右端可能比23:00刻度多延出一段（实测image(3)延出26px），
        直接拿蓝线端点当23:00会让晚间时段采样位置偏晚、读数系统性偏低
        （22:15曾读到58708，真值62663）。左端点=00:15在完整图/裁剪图
        两类样本上均验证可靠；竖线x与tooltip时间是两个独立量测，
        以左端点+竖线反推px/h并重算右端点。Dashboard完整图本身无延出，
        修正量<3px自动跳过，行为不变。"""
        if axis is None:
            return axis
        x0_line, x1_line = sorted(axis.x_pixel_range)
        span = x1_line - x0_line
        if span < 100:
            return axis
        x, y, w, h = rect

        # 0) 刻度标签连通域拟合（像素级精确，优先于hover锚点）
        tick_rng = self._fit_load_x_axis_by_ticks(img, rect, axis, texts)
        if tick_rng is not None:
            if abs(tick_rng[0] - x0_line) > 3 or abs(tick_rng[1] - x1_line) > 3:
                print(f"[INFO] 负荷X轴刻度拟合修正: "
                      f"({x0_line},{x1_line}) -> {tick_rng[:2]}")
                return AxisInfo(x_min=axis.x_min, x_max=axis.x_max,
                                y_min=axis.y_min, y_max=axis.y_max,
                                x_pixel_range=(tick_rng[0], tick_rng[1]),
                                y_pixel_range=axis.y_pixel_range)
            return axis

        # 1) tooltip时间：只接受完整HH:MM（分钟已知），整点占位不用
        hover_t = None
        inner = [t for t in texts
                 if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h
                 and t["center_y"] <= y + h * 0.45]
        inner.sort(key=lambda t: (t["center_y"], t["center_x"]))
        for t in inner:
            m = re.search(r'(?<!\d)([01]?\d|2[0-3])\s*[:：]\s*([0-5]\d)(?!\d)',
                          t["text"])
            if m:
                hover_t = int(m.group(1)) + int(m.group(2)) / 60.0
                break
        if hover_t is None:
            hover_t = self._refine_load_tooltip_time_by_ocr(img, rect)
        if (hover_t is None or hover_t < axis.x_min + 2.0 or
                hover_t > axis.x_max):
            return axis

        # 2) 蓝色竖线x像素（独立量测）
        hover_x = self._detect_load_hover_line_x(img, rect, axis)
        if hover_x is None:
            return axis
        # 竖线须在绘图区内部（>20%跨度），防止误检Y轴/边缘
        if not (x0_line + span * 0.20 < hover_x < x1_line - 2):
            return axis

        # 3) 双锚点重算右端点：x0_line(=00:15) + px/h * 22.75h
        px_per_h = (hover_x - x0_line) / (hover_t - axis.x_min)
        x1_refined = x0_line + px_per_h * (axis.x_max - axis.x_min)
        delta = x1_refined - x1_line
        if abs(delta) <= 3:
            return axis
        if abs(delta) > span * 0.10:
            print(f"[WARN] 负荷X轴hover修正幅度{delta:+.0f}px异常"
                  f"(>{span * 0.10:.0f}px)，放弃修正")
            return axis
        refined = AxisInfo(x_min=axis.x_min, x_max=axis.x_max,
                           y_min=axis.y_min, y_max=axis.y_max,
                           x_pixel_range=(x0_line, int(round(x1_refined))),
                           y_pixel_range=axis.y_pixel_range)
        print(f"[INFO] 负荷X轴hover双锚点修正: 竖线x={hover_x}@{hover_t:.2f}h, "
              f"右端点{x1_line}->{refined.x_pixel_range[1]} ({delta:+.0f}px)")
        return refined

    def _rescue_load_axis_geometry(self, img: np.ndarray,
                                   rect: Tuple[int, int, int, int],
                                   axis: AxisInfo,
                                   legend_boxes: Optional[List]) -> Optional[AxisInfo]:
        """负荷曲线退化时，用蓝色X轴、图例底部和首条网格线重建0~100000轴。"""
        x, y, w, h = rect
        roi = img[y:y + h, x:x + w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([92, 45, 80]), np.array([125, 255, 255]))

        # X轴蓝线：下半幅面中蓝色像素最多且横跨较宽的一行
        row_scores = (blue > 0).sum(axis=1)
        candidates = [(int(s), yy) for yy, s in enumerate(row_scores)
                      if yy > h * 0.55 and s > max(30, w * 0.20)]
        if candidates:
            _, y_bottom_rel = max(candidates)
        else:
            y_bottom_rel = int(max(axis.y_pixel_range) - y)

        # 图例底部之后的第一条浅色水平网格线=100000刻度线
        if legend_boxes:
            legend_bottom = max(max(p[1] for p in bb) for bb in legend_boxes) - y
        else:
            legend_bottom = int(h * 0.25)
        x0a, x1a = axis.x_pixel_range
        rx0 = max(0, int(min(x0a, x1a) - x))
        rx1 = min(w, int(max(x0a, x1a) - x))
        y_top_rel = None
        for yy in range(max(0, legend_bottom + 1), max(legend_bottom + 2, y_bottom_rel - 40)):
            row = hsv[yy, rx0:rx1]
            neutral = (row[:, 1] < 25) & (row[:, 2] > 145) & (row[:, 2] < 250)
            if neutral.sum() > max(20, (rx1 - rx0) * 0.08):
                y_top_rel = yy
                break
        if y_top_rel is None:
            y_top_rel = legend_bottom + 3
        if y_bottom_rel - y_top_rel < 80:
            return None

        rescued = AxisInfo(x_min=axis.x_min, x_max=axis.x_max,
                           y_min=0.0, y_max=100000.0,
                           x_pixel_range=axis.x_pixel_range,
                           y_pixel_range=(y + y_top_rel, y + y_bottom_rel))
        print(f"[WARN] 负荷轴几何重建: Y像素=({y + y_top_rel},{y + y_bottom_rel}), "
              f"范围0~100000")
        return rescued

    def _synthesize_dashed_from_anchor(self, solid_curve: CurveData,
                                       axis: AxisInfo, gap_px: float,
                                       pred_name: str,
                                       color_name: str) -> Optional[CurveData]:
        """V5.0：虚线全天被实线遮蔽（预测≈实际）时的锚点差合成兜底。
        gap_px = 实际值-预测值 换算的像素差（_extract_load_style_curves
        中按tooltip锚点计算）；预测像素 = 实线像素 + gap_px。"""
        if not solid_curve.pixel_points:
            return None
        mw_per_px = (axis.y_max - axis.y_min) / max(
            abs(axis.y_pixel_range[1] - axis.y_pixel_range[0]), 1)
        pixel_points = [(xx, int(round(yy + gap_px)))
                        for xx, yy in solid_curve.pixel_points]
        curve = CurveData(name=pred_name, color_name=color_name)
        curve.pixel_points = pixel_points
        curve.points = self._pixel_to_real(pixel_points, axis)
        curve.confidence = 0.5   # 合成曲线：形态为近似，锚点时刻精确
        curve._axis = axis
        curve._synthesized = True
        curve._no_smooth = True
        print(f"[INFO] 负荷{pred_name}虚线全天被实线遮蔽，"
              f"以实线+锚点差({gap_px:+.1f}px≈{gap_px * mw_per_px:+.0f}MW)合成")
        return curve

    def _extract_dashed_below_curve(self, mask: np.ndarray, axis: AxisInfo,
                                    solid_curve: CurveData,
                                    color_name: str,
                                    core_mask: np.ndarray = None,
                                    anchor_gap_px: float = None
                                    ) -> Optional[CurveData]:
        """
        在实线路径附近提取同色虚线（负荷面板预测曲线专用）。

        V4.5：虚线可能在实线上方(预测>实际，20260502实测)或下方，且常与
        实线近乎重合。主路：高饱和核掩码(S>=130)在实线±35px窗口内剔除
        实线自身(-2~+6)后取最近簇作为短划，量测“虚线-实线”竖直偏移并
        对全天插值合成——填充(S55~62)在核掩码中不可见，不会被当虚线；
        核掩码命中过少时(如20260501 Dashboard的低饱和细虚线)退回全掩码
        下方搜索的老逻辑(读取粘连团下缘/填充顶作为近似)。
        """
        if solid_curve is None or not solid_curve.pixel_points:
            return None

        sx = np.array([p[0] for p in solid_curve.pixel_points], dtype=float)
        sy = np.array([p[1] for p in solid_curve.pixel_points], dtype=float)
        order = np.argsort(sx)
        sx, sy = sx[order], sy[order]
        x0, x1 = int(sx[0]), int(sx[-1])

        # ---------- 主路：核掩码双侧偏移量测 + 全天插值 ----------
        if core_mask is not None:
            offsets = []
            for xx in range(x0, x1 + 1):
                ay = float(np.interp(xx, sx, sy))
                rows = np.where(core_mask[:, xx] > 0)[0]
                rows = rows[(rows >= ay - 35) & (rows <= ay + 35)]
                if len(rows) == 0:
                    continue
                # 聚簇(gap<=2)：实线簇=含ay的簇，虚线=最近的其他簇(>=2px)。
                # 与实线粘连(<=1px缝)时合为一簇->该列视为重合不采样，
                # 避免把实线自己的下边缘当虚线。
                clusters, cur = [], [int(rows[0])]
                for rr in rows[1:]:
                    rr = int(rr)
                    if rr - cur[-1] <= 2:
                        cur.append(rr)
                    else:
                        clusters.append(cur)
                        cur = [rr]
                clusters.append(cur)
                solid_cl = None
                for c in clusters:
                    if c[0] - 1 <= ay <= c[-1] + 1:
                        solid_cl = c
                        break
                others = [c for c in clusters
                          if c is not solid_cl and len(c) >= 2]
                if not others:
                    continue
                best = min(others,
                           key=lambda c: min(abs(c[0] - ay), abs(c[-1] - ay)))
                offsets.append((xx, float(np.mean(best)) - ay))
            # V5.0c：锚点差方向一致性过滤——虚线被实线遮住时，填充上沿
            # 会成为“最近的其他簇”，给出反向假偏移（05-03预测直调中午
            # 读到实线下方填充≈-3000，而tooltip证其应在上方+1720）。
            # 锚点差>1.5px时丢弃符号相反且>1.5px的样本（填充假偏移
            # 恒定-4~-7px），保留的真短划偏移跨断档插值。
            if anchor_gap_px is not None and abs(anchor_gap_px) > 1.5:
                _pos = anchor_gap_px > 0
                _kept = [o for o in offsets
                         if abs(o[1]) <= 1.5 or (o[1] > 0) == _pos]
                if len(_kept) < len(offsets):
                    print(f"[INFO] 负荷{color_name}虚线偏移方向过滤: "
                          f"丢弃{len(offsets) - len(_kept)}个反向样本"
                          f"（锚点差{anchor_gap_px:+.1f}px，填充假偏移）")
                offsets = _kept
            if len(offsets) >= 12:
                ox = np.array([o[0] for o in offsets], dtype=float)
                oy = np.array([o[1] for o in offsets], dtype=float)
                # 滚动中值去离群(圆环残弧/噪声)
                oy_med = pd.Series(oy).rolling(
                    9, center=True, min_periods=1).median().to_numpy()
                bad = np.abs(oy - oy_med) > 8
                if bad.any() and (~bad).sum() >= 3:
                    ox, oy_med = ox[~bad], oy_med[~bad]
                full_x = np.arange(x0, x1 + 1)
                off_full = np.interp(full_x, ox, oy_med)
                # 采样区外(虚线与实线视觉上重合的时段)用tooltip锚点差
                # 填充——该处两线本就读不出差别，锚点差是最合理估计
                if anchor_gap_px is not None:
                    left = full_x < ox[0]
                    right = full_x > ox[-1]
                    off_full[left] = anchor_gap_px
                    off_full[right] = anchor_gap_px
                off_full = pd.Series(off_full).rolling(
                    9, center=True, min_periods=1).median().to_numpy()
                pixel_points = [
                    (int(xx), int(round(float(np.interp(xx, sx, sy)) +
                                        off_full[xx - x0])))
                    for xx in full_x]
                curve = CurveData(name="虚线曲线", color_name=color_name)
                curve.pixel_points = pixel_points
                curve.points = self._pixel_to_real(pixel_points, axis)
                curve.confidence = 0.66
                curve._axis = axis
                return curve
            print(f"[INFO] 负荷{color_name}虚线核掩码命中{len(offsets)}列<12，"
                  f"退回全掩码下方搜索")

        # ---------- 退路：全掩码下方搜索 ----------
        # V5.0c：锚点差证虚线在实线上方时，下方搜索必读到填充
        # （05-03预测直调中午的-3000假凹陷），返回None交给锚点差
        # 合成（锚点时刻精确）；仅锚点差>+1.5px才跳过，虚线在下方
        # 或未知时下方搜索仍是有效退路（05-01/image(3)验证过）。
        if anchor_gap_px is not None and anchor_gap_px < -1.5:
            print(f"[INFO] 负荷{color_name}虚线锚点差{anchor_gap_px:+.1f}px"
                  f"（在实线上方），下方搜索必读填充，交锚点差合成")
            return None
        points = []
        for xx in range(x0, x1 + 1):
            actual_y = float(np.interp(xx, sx, sy))
            rows = np.where(mask[:, xx] > 0)[0]
            # V4.4：起点+4(越过实线线芯3~5px)、簇宽>=2px(跳过1px抗锯齿
            # 残丝)。原+2起点会把实线下边缘当虚线(image(3)14:15曾读
            # 49,090，真值46,487)。
            rows = rows[(rows > actual_y + 4) & (rows < actual_y + 35)]
            if len(rows) == 0:
                continue
            # 第一段连续簇=虚线笔画；更下方通常是填充/网格噪声
            clusters, cur = [], [int(rows[0])]
            for rr in rows[1:]:
                rr = int(rr)
                if rr - cur[-1] <= 4:
                    cur.append(rr)
                else:
                    clusters.append(cur)
                    cur = [rr]
            clusters.append(cur)
            cl = next((c for c in clusters if len(c) >= 2), clusters[0])
            points.append((xx, float(min(cl) + 1.0)))

        if len(points) < 30:
            return None

        # 缺失列插值 + 滚动中值离群校正
        px = np.array([p[0] for p in points], dtype=float)
        py = np.array([p[1] for p in points], dtype=float)
        full_x = np.arange(px[0], px[-1] + 1)
        full_y = np.interp(full_x, px, py)
        med = pd.Series(full_y).rolling(9, center=True, min_periods=1).median().to_numpy()
        bad = np.abs(full_y - med) > 15
        if bad.any() and (~bad).sum() >= 3:
            full_y[bad] = np.nan
            good = ~np.isnan(full_y)
            full_y = np.interp(full_x, full_x[good], full_y[good])

        curve = CurveData(name="虚线曲线", color_name=color_name)
        curve.pixel_points = [(int(xx), int(round(yy))) for xx, yy in zip(full_x, full_y)]
        curve.points = self._pixel_to_real(curve.pixel_points, axis)
        curve.confidence = 0.66
        curve._axis = axis  # V4.3：坐标轴随曲线绑定
        return curve

    def _extract_load_style_curves(self, img: np.ndarray,
                                   roi: Tuple[int, int, int, int],
                                   axis: AxisInfo,
                                   legend_boxes: Optional[List] = None,
                                   tooltip_anchor: Optional[Dict] = None
                                   ) -> List[CurveData]:
        """
        负荷面板专用提取：同色系“实线/虚线”分离。

        该Dashboard负荷面板的配色规则与出力面板不同：
        - 预测直调负荷 = 青绿虚线；实际直调负荷 = 青绿实线；
        - 预测全网负荷 = 橙黄虚线；实际全网负荷 = 橙黄实线。
        仅按色相提取会把预测/实际混成一条曲线；低饱和度阈值又会把面积填充
        误认为曲线。这里使用高饱和度线像素 + 水平开运算：
        - 连续长线 → 实线（实际）；
        - 原线像素减去实线带 → 横向闭运算连接短划线 → 虚线（预测）。
        """
        x, y, w, h = roi
        roi_img = img[y:y + h, x:x + w]
        self._px_offset = (x, y)
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

        # 绘图区裁剪（与_mask_to_curve一致，略放宽X以覆盖24:00）
        x0a, x1a = axis.x_pixel_range
        y0a, y1a = axis.y_pixel_range
        xspan = abs(x1a - x0a)
        cx0 = max(0, int(min(x0a, x1a) - x - xspan * 0.03))
        cx1 = min(w, int(max(x0a, x1a) - x + xspan * 0.05))
        cy0 = max(0, int(min(y0a, y1a) - y - 8))
        cy1 = min(h, int(max(y0a, y1a) - y + 8))
        if cx1 <= cx0 or cy1 <= cy0:
            return []

        specs = [
            # family, HSV范围, 预测列名, 实际列名
            # V4.4：青色统一为H72~96/S>=48——旧双区间在H=80、S=55~64处
            # 留有缺口，抗锯齿的线顶像素(如H=80,S=55)会漏检，导致曲线
            # 顶边下移1~2px(≈500~1000MW)；橙色下限S65->50同理补线顶。
            ("direct", [[(72, 48, 100), (96, 255, 255)]],
             "预测直调负荷", "实际直调负荷"),
            ("full", [[(10, 50, 120), (30, 255, 255)]],
             "预测全网负荷", "实际全网负荷"),
        ]
        curves = []

        # V4.4：hover竖线位置——蓝色竖线本身会抹除曲线，且ECharts在竖线
        # 处对每条曲线绘制半径~13px的空心圆环标记，圆环上/下弧会被当成
        # 曲线（实测：实际全网11:00读到圆环顶86,964，真值~81,500；预测
        # 直调读到下弧37,878，真值~40,300——邻域偏差达±5,000）。提取前
        # 挖除竖线±16px畸变列由插值桥接，tooltip锚点再写入精确值；圆环
        # 校正同时限定在该位置附近（挖除后此处无环可校正，双重保险），
        # 远处同色“实线+虚线对”也不再被误判为圆环拉到两线中点。
        hover_x = self._detect_load_hover_line_x(img, roi, axis)
        self._ring_correct_near_x = (hover_x - x) if hover_x is not None else -10**9

        # V4.5：各色系“虚线-实线”tooltip锚点差(px)。虚线与实线视觉重合
        # 的时段(预测≈实际的日子)无短划可采样，用锚点差作为该时段偏移。
        anchor_gaps = {}
        if tooltip_anchor and tooltip_anchor.get("time") is not None:
            mw_per_px = (axis.y_max - axis.y_min) / max(
                abs(axis.y_pixel_range[1] - axis.y_pixel_range[0]), 1)
            for family, _, pred_name, act_name in specs:
                pv, av = (tooltip_anchor["values"].get(pred_name),
                          tooltip_anchor["values"].get(act_name))
                if pv is not None and av is not None:
                    anchor_gaps[family] = (av - pv) / mw_per_px

        for family, ranges, pred_name, act_name in specs:
            base = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in ranges:
                base |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                                    np.array(hi, dtype=np.uint8))
            clipped = np.zeros_like(base)
            clipped[cy0:cy1, cx0:cx1] = base[cy0:cy1, cx0:cx1]
            base = clipped

            # V3.8：剔除图例文字及其左侧色块。单面板裁剪图中图例位于
            # 绘图区顶部，若不排除，DP会把图例色块当成曲线，造成常数/错位。
            for bbox in (legend_boxes or []):
                xs_bb = [int(p[0]) for p in bbox]
                ys_bb = [int(p[1]) for p in bbox]
                lx0 = max(0, min(xs_bb) - x - 42)   # 覆盖左侧图例色条
                lx1 = min(w, max(xs_bb) - x + 8)
                ly0 = max(0, min(ys_bb) - y - 7)
                ly1 = min(h, max(ys_bb) - y + 7)
                if lx1 > lx0 and ly1 > ly0:
                    base[ly0:ly1, lx0:lx1] = 0

            # V4.4：挖除hover竖线/圆环畸变区（±16px≈±0.55h）
            if hover_x is not None:
                hx = hover_x - x
                base[:, max(0, hx - 16):min(w, hx + 17)] = 0

            if cv2.countNonZero(base) < 80:
                print(f"[WARN] 负荷{family}色系线像素不足，无法分离实线/虚线")
                continue

            # 1) 实线（实际负荷）：高饱和度掩码的每列最上簇就是连续实线，
            # 直接走DP路径追踪。不要用水平开运算——曲线有坡度时会把实线误删。
            solid_curve = self._mask_to_curve(
                base, axis, "cyan" if family == "direct" else "orange")

            # 2) 虚线（预测负荷）：核掩码偏移量测为主、全掩码下方搜索兜底。
            # 核掩码继承base的全部剔除(图例/裁剪/hover畸变区)；锚点差
            # 用于填充虚线与实线视觉重合的时段。
            core = cv2.inRange(hsv,
                               np.array((ranges[0][0][0], 130, 120), dtype=np.uint8),
                               np.array((ranges[0][1][0], 255, 255), dtype=np.uint8))
            core = cv2.bitwise_and(core, base)
            dashed_curve = self._extract_dashed_below_curve(
                base, axis, solid_curve,
                "cyan" if family == "direct" else "orange",
                core_mask=core,
                anchor_gap_px=anchor_gaps.get(family))

            if dashed_curve is not None and len(dashed_curve.pixel_points) >= 30:
                dashed_curve.name = pred_name
                dashed_curve.confidence = 0.68
                # 直调虚线与填充色接近，强平滑会把11:15低谷再压低；
                # 全网虚线较干净，可用5点轻平滑去毛刺
                dashed_curve._no_smooth = (family == "direct")
                dashed_curve._smooth_window = 5
                curves.append(dashed_curve)
            else:
                print(f"[WARN] 负荷{family}虚线提取失败: {pred_name}")
                # V5.0：预测≈实际到全天像素级重合的日子（如05-03预测
                # 全网），虚线图上零可见、任何像素法都读不出。tooltip
                # 同时给出预测/实际锚点时，用“实线+锚点差”合成虚线：
                # 形态跟随实线（该日两线本就几乎重合，是合理近似），
                # 锚点时刻精确等于tooltip值；峰值标注守卫可再吸附
                # 图上印刷的当日峰值（如84065）。
                _gap = anchor_gaps.get(family)
                if (solid_curve is not None and _gap is not None and
                        len(solid_curve.pixel_points) >= 30):
                    dashed_curve = self._synthesize_dashed_from_anchor(
                        solid_curve, axis, _gap, pred_name,
                        "cyan" if family == "direct" else "orange")
                    if dashed_curve is not None:
                        curves.append(dashed_curve)

            if solid_curve is not None and len(solid_curve.pixel_points) >= 30:
                solid_curve.name = act_name
                solid_curve.confidence = 0.74
                solid_curve._smooth_window = 5
                curves.append(solid_curve)
            else:
                print(f"[WARN] 负荷{family}实线提取失败: {act_name}")

        self._ring_correct_near_x = None
        print(f"[INFO] 负荷面板实线/虚线分离: {len(curves)}条 "
              f"({', '.join(c.name for c in curves)})")
        return curves

    def _extract_load_curves_visual_fallback(
            self, img: np.ndarray, roi: Tuple[int, int, int, int],
            axis: AxisInfo, legend_boxes: Optional[List] = None,
            tooltip_anchor: Optional[Dict] = None) -> List[CurveData]:
        """
        V4.3独立兜底：主提取退化为直线时启用的第二数据源。
        与_extract_load_style_curves完全独立的代码路径：
        不做连通域过滤、不做DP路径追踪，直接逐列对色系掩码聚簇，
        实线=该列最上簇中心，虚线=实线下方2~35px第一段簇。
        逐列覆盖>=60%绘图宽度才接受，杜绝边框/图例像素被插值成直线。
        """
        x, y, w, h = roi
        roi_img = img[y:y + h, x:x + w]
        self._px_offset = (x, y)
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

        x0a, x1a = axis.x_pixel_range
        y0a, y1a = axis.y_pixel_range
        cx0 = max(0, int(min(x0a, x1a) - x))
        cx1 = min(w, int(max(x0a, x1a) - x))
        cy0 = max(0, int(min(y0a, y1a) - y - 6))
        cy1 = min(h, int(max(y0a, y1a) - y + 6))
        if cx1 <= cx0 + 50 or cy1 <= cy0 + 40:
            return []

        specs = [
            # V4.4：与主提取一致的补线顶色域（消除H=80/S=55~64缺口）
            ("direct", [[(72, 48, 100), (96, 255, 255)]],
             "预测直调负荷", "实际直调负荷"),
            ("full", [[(10, 50, 120), (30, 255, 255)]],
             "预测全网负荷", "实际全网负荷"),
        ]
        curves = []
        # V4.4：与主提取一致，挖除hover竖线/圆环畸变区
        hover_x = self._detect_load_hover_line_x(img, roi, axis)
        for family, ranges, pred_name, act_name in specs:
            base = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in ranges:
                base |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                                    np.array(hi, dtype=np.uint8))
            clipped = np.zeros_like(base)
            clipped[cy0:cy1, cx0:cx1] = base[cy0:cy1, cx0:cx1]
            base = clipped
            for bbox in (legend_boxes or []):
                xs_bb = [int(p[0]) for p in bbox]
                ys_bb = [int(p[1]) for p in bbox]
                lx0 = max(0, min(xs_bb) - x - 42)
                lx1 = min(w, max(xs_bb) - x + 8)
                ly0 = max(0, min(ys_bb) - y - 7)
                ly1 = min(h, max(ys_bb) - y + 7)
                if lx1 > lx0 and ly1 > ly0:
                    base[ly0:ly1, lx0:lx1] = 0
            if hover_x is not None:
                hx = hover_x - x
                base[:, max(0, hx - 16):min(w, hx + 17)] = 0
            base = cv2.morphologyEx(base, cv2.MORPH_OPEN,
                                    np.ones((2, 2), np.uint8))
            if cv2.countNonZero(base) < 100:
                continue

            # 实线：逐列最上簇顶+1（独立直采，不用DP/连通域）。
            # V4.5：原取簇中心——填充(S55~62)在掩码内时中心被拉到填充
            # 中部，读数偏低20~30%(20260502兜底曾读55,376，真值67,289)。
            points = []
            for xx in range(cx0, cx1):
                rows = np.where(base[:, xx] > 0)[0]
                if len(rows) == 0:
                    continue
                clusters, cur = [], [int(rows[0])]
                for rr in rows[1:]:
                    rr = int(rr)
                    if rr - cur[-1] <= 6:
                        cur.append(rr)
                    else:
                        clusters.append(cur)
                        cur = [rr]
                clusters.append(cur)
                top = clusters[0]
                points.append((xx, float(min(top) + 1.0)))
            min_cols = int((cx1 - cx0) * 0.60)
            if len(points) < max(60, min_cols):
                print(f"[WARN] 兜底提取{family}实线覆盖不足: "
                      f"{len(points)}列 < {max(60, min_cols)}")
                continue
            px_arr = np.array([p[0] for p in points], dtype=float)
            py_arr = np.array([p[1] for p in points], dtype=float)
            full_x = np.arange(px_arr[0], px_arr[-1] + 1)
            full_y = np.interp(full_x, px_arr, py_arr)
            med = pd.Series(full_y).rolling(11, center=True,
                                            min_periods=1).median().to_numpy()
            bad = np.abs(full_y - med) > 18
            if bad.any() and (~bad).sum() >= 5:
                full_y[bad] = np.nan
                good = ~np.isnan(full_y)
                full_y = np.interp(full_x, full_x[good], full_y[good])

            solid = CurveData(name=act_name,
                              color_name="cyan" if family == "direct" else "orange")
            solid.pixel_points = [(int(xx), int(round(yy)))
                                  for xx, yy in zip(full_x, full_y)]
            solid.points = self._pixel_to_real(solid.pixel_points, axis)
            solid.confidence = 0.64
            solid._axis = axis
            solid._smooth_window = 5
            curves.append(solid)

            # V4.5：与主提取一致，传入核掩码与锚点差
            core = cv2.inRange(hsv,
                               np.array((ranges[0][0][0], 130, 120), dtype=np.uint8),
                               np.array((ranges[0][1][0], 255, 255), dtype=np.uint8))
            core = cv2.bitwise_and(core, base)
            _gap = None
            if tooltip_anchor and tooltip_anchor.get("values"):
                _pv = tooltip_anchor["values"].get(pred_name)
                _av = tooltip_anchor["values"].get(act_name)
                if _pv is not None and _av is not None:
                    _mw = (axis.y_max - axis.y_min) / max(
                        abs(axis.y_pixel_range[1] - axis.y_pixel_range[0]), 1)
                    _gap = (_av - _pv) / _mw
            dashed = self._extract_dashed_below_curve(
                base, axis, solid,
                "cyan" if family == "direct" else "orange",
                core_mask=core, anchor_gap_px=_gap)
            if dashed is not None and len(dashed.pixel_points) >= 30:
                dashed.name = pred_name
                dashed.confidence = 0.62
                dashed._no_smooth = (family == "direct")
                dashed._smooth_window = 5
                curves.append(dashed)

        print(f"[INFO] 负荷独立视觉兜底: {len(curves)}条 "
              f"({', '.join(c.name for c in curves)})")
        return curves

    def _extract_by_edge(self, roi_img: np.ndarray, axis: AxisInfo) -> List[CurveData]:
        """基于边缘检测提取曲线"""
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)

        # 去除网格线（假设网格线较细且亮度中等）
        # 使用形态学闭运算
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        temp = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
        temp = cv2.morphologyEx(temp, cv2.MORPH_CLOSE, kernel)

        # 自适应阈值
        binary = cv2.adaptiveThreshold(temp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)

        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        roi_h, roi_w = roi_img.shape[:2]
        curves = []
        for cnt in contours:
            if len(cnt) < self.config["chart"]["min_curve_points"]:
                continue

            # ============ 形状过滤（排除文字/图例/边框/网格线） ============
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw < roi_w * 0.35:
                continue  # 曲线必须横跨图表35%以上宽度（文字块/图例被排除）
            if bw > roi_w * 0.97 and bh > roi_h * 0.97:
                continue  # 图表外边框
            if bh < roi_h * 0.02:
                continue  # 近水平直线（坐标轴/网格线）

            # 拟合曲线
            points = [(int(p[0][0]), int(p[0][1])) for p in cnt]

            # 去重并按X排序
            points = self._deduplicate_and_sort(points)

            if len(points) >= self.config["chart"]["min_curve_points"]:
                curve = CurveData(name="边缘曲线", color_name="unknown")
                curve.pixel_points = points
                curve.points = self._pixel_to_real(points, axis)
                curve.confidence = 0.6
                curves.append(curve)

        return curves

    def _extract_generic(self, roi_img: np.ndarray, axis: AxisInfo) -> List[CurveData]:
        """通用曲线提取（基于亮度差异）"""
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)

        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 计算每列的亮度变化
        h, w = blurred.shape
        curve_points = []

        for col in range(w):
            column = blurred[:, col]
            # 找到亮度极值点（假设曲线与背景有明显对比）
            # 使用局部最大值
            smoothed = savgol_filter(column, min(11, len(column)//2*2+1), 2)

            # 找到最显著的峰/谷
            peak_idx = np.argmax(smoothed)
            valley_idx = np.argmin(smoothed)

            # 选择变化更显著的那个
            if smoothed[peak_idx] - np.mean(smoothed) > np.mean(smoothed) - smoothed[valley_idx]:
                row = peak_idx
            else:
                row = valley_idx

            curve_points.append((col, row))

        if len(curve_points) >= self.config["chart"]["min_curve_points"]:
            curve = CurveData(name="通用曲线", color_name="unknown")
            curve.pixel_points = curve_points
            curve.points = self._pixel_to_real(curve_points, axis)
            curve.confidence = 0.5
            return [curve]

        return []

    def _erase_plot_text(self, mask: np.ndarray,
                         cx0: int, cx1: int, cy0: int, cy1: int):
        """V4.6c：把绘图区内OCR文字框从掩码中挖除（就地修改）。
        峰值标注与曲线同色且在绘图区内，会被当成大组件/延伸目标。"""
        ox, oy = getattr(self, "_px_offset", (0, 0))
        texts = getattr(self, "text_data_all", None) or []
        for t in texts:
            bbox = t.get("bbox")
            if not bbox:
                continue
            try:
                bxs = [p[0] - ox for p in bbox]
                bys = [p[1] - oy for p in bbox]
            except Exception:
                continue
            tx0, tx1 = int(min(bxs)) - 2, int(max(bxs)) + 2
            ty0, ty1 = int(min(bys)) - 2, int(max(bys)) + 2
            if tx1 < cx0 or tx0 > cx1 or ty1 < cy0 or ty0 > cy1:
                continue
            mask[max(ty0, cy0):min(ty1, cy1),
                 max(tx0, cx0):min(tx1, cx1)] = 0

    def _mask_to_curve(self, mask: np.ndarray, axis: AxisInfo, color_name: str) -> Optional[CurveData]:
        """将二值掩码转换为曲线数据（V2：先裁剪到绘图区，剔除区外同色文字/图例）"""
        # ==================== 关键：掩码裁剪到绘图区 ====================
        # 峰值标注文字（如蓝色"715.93"）与曲线同色，但都位于Y轴最高刻度线之上；
        # 图例色块位于绘图区外。裁剪后这些污染像素全部清零。
        ox, oy = getattr(self, "_px_offset", (0, 0))
        h_m, w_m = mask.shape
        x_span = abs(axis.x_pixel_range[1] - axis.x_pixel_range[0])
        mx = int(x_span * 0.05)          # X向放宽5%（坐标标签未覆盖绘图区边缘）
        my = 5                            # Y向仅放宽5px（严格挡住上方标注文字）
        cx0 = max(0, int(min(axis.x_pixel_range) - ox - mx))
        cx1 = min(w_m, int(max(axis.x_pixel_range) - ox + mx))
        cy0 = max(0, int(min(axis.y_pixel_range) - oy - my))
        cy1 = min(h_m, int(max(axis.y_pixel_range) - oy + my))
        if cx1 > cx0 and cy1 > cy0:
            clipped = np.zeros_like(mask)
            clipped[cy0:cy1, cx0:cx1] = mask[cy0:cy1, cx0:cx1]
            mask = clipped

        # ==================== V4.6c：挖除绘图区内OCR文字框 ====================
        # 峰值标注（如蓝色"69869.00"）与曲线同色、且位于绘图区内部
        # （Y轴放宽5px挡不住——文字在网格线之下）。标注是大连通域，
        # DP骨干会直接锁到文字下沿，96点被钳成标注值的平顶
        # （全网发电预测出力曾8:45提前“达峰”69869并平台化）；
        # 碎片延伸也会误锁文字下沿。文字对曲线提取纯为污染，挖除后
        # 由DP/插值桥接（文字下的真线仅损失数列）。
        self._erase_plot_text(mask, cx0, cx1, cy0, cy1)

        # ==================== 连通域过滤：只保留大组件 ====================
        # 曲线（含面积填充）是最大连通域；绘图区内部的标注文字
        # （如蓝色"13941.00"）是孤立小碎块，全部丢弃
        # V4.6：过滤前先留存完整掩码——半透明填充上的线段被洗淡后会
        # 碎成若干<10%阈值的小组件（05-02非市场化/全网/风电的实时出力
        # 后半段全部因此丢失，插值钳成恒值直线），后续用碎片接续补回。
        mask_unfiltered = mask
        num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if num > 2:  # 背景+至少2个前景组件才需要过滤
            areas = stats[1:, cv2.CC_STAT_AREA]
            max_area = areas.max()
            big_ids = [i + 1 for i, a in enumerate(areas) if a > max_area * 0.1]
            mask = np.isin(labels, big_ids).astype(np.uint8) * 255

        # 获取所有非零像素
        ys, xs = np.where(mask > 0)
        if len(xs) < self.config["chart"]["min_curve_points"]:
            return None

        # ==================== DP路径追踪（抗绘图区内文字污染） ====================
        # 真实曲线是连续轨迹；标注文字（如绿色"538.50"）浮在曲线上方，
        # 按列取上边缘会被文字带飞。改为：每列把像素聚成若干候选簇，
        # 用动态规划选"列间跳变最小"的路径——文字碎片造成跳变，被自然绕过。
        col_rows = {}
        for xx, yy in zip(xs, ys):
            col_rows.setdefault(xx, []).append(yy)

        # 每列候选簇：行距>6px分簇，取簇顶（兼容面积填充图，簇顶=线条上边缘）
        cand = {}
        col_cl = {}
        for xx, rows in col_rows.items():
            rows = sorted(rows)
            clusters, cur = [], [rows[0]]
            for r in rows[1:]:
                if r - cur[-1] <= 6:
                    cur.append(r)
                else:
                    clusters.append(cur)
                    cur = [r]
            clusters.append(cur)
            col_cl[xx] = clusters
            cand[xx] = [float(min(cl)) + 1.0 for cl in clusters]

        cols = sorted(cand.keys())
        if len(cols) < 2:
            points = [(c0, int(cand[c0][0])) for c0 in cols]
        else:
            # DP：cost = (Δrow)²/gap，缺失列按列距惩罚
            dp = [[0.0] * len(cand[cols[0]])]
            parent = [[-1] * len(cand[cols[0]])]
            for i in range(1, len(cols)):
                gap = max(cols[i] - cols[i-1], 1)
                dpi, pari = [], []
                for r in cand[cols[i]]:
                    best, bj = 1e18, -1
                    for j, pr in enumerate(cand[cols[i-1]]):
                        cst = dp[-1][j] + ((r - pr) ** 2) / gap
                        if cst < best:
                            best, bj = cst, j
                    dpi.append(best)
                    pari.append(bj)
                dp.append(dpi)
                parent.append(pari)
            # 回溯最优路径
            j = int(np.argmin(dp[-1]))
            path = []
            for i in range(len(cols) - 1, -1, -1):
                path.append((cols[i], cand[cols[i]][j]))
                j = parent[i][j]
            path.reverse()

            # ---- 圆环标记校正：数据点标记是空心圆，圆心才是真值 ----
            # DP路径在标记列易骑上/下圆弧而虚高/虚低一个半径（如非市场化预测
            # 13941被抬到15366、实时43647.98被抬到45395）。检测圆环run
            # （同列2簇、上簇<=8px、簇间距<=16px；标注文字与线间距更大，被排除），
            # 圆心=两簇内沿中点，run取中位数，run间线性插值，
            # 路径偏离>1.5px处改写回圆心/插值线。沙箱实测：非市场化预测
            # 15675->14054(+0.81%)、实时45405->43514(-0.31%)。
            ring_mid_col = {}
            for xx, clusters in col_cl.items():
                if len(clusters) == 2:
                    sp0 = max(clusters[0]) - min(clusters[0])
                    gap2 = min(clusters[1]) - max(clusters[0])
                    if sp0 <= 8 and gap2 <= 16:
                        ring_mid_col[xx] = (max(clusters[0]) + min(clusters[1])) / 2.0
            rcols = sorted(ring_mid_col)
            runs, cur_run = [], [rcols[0]] if rcols else []
            for c in rcols[1:]:
                if c - cur_run[-1] <= 3:
                    cur_run.append(c)
                else:
                    runs.append(cur_run)
                    cur_run = [c]
            if cur_run:
                runs.append(cur_run)
            ring_runs = [(float(np.mean(run)), float(np.median([ring_mid_col[c] for c in run])))
                         for run in runs if len(run) >= 2]

            # V4.4：负荷面板同色系“实线+虚线”相距7~16px时恰好满足圆环
            # 判据（上簇<=8px、簇间距<=16px），会被误判为圆环上/下弧，
            # 校正把路径拉到两线中点——image(3)午后爬坡段实线曾因此偏低
            # ~3000MW(14:15真值~50000被写成46467)。负荷面板的真圆环只
            # 存在于hover竖线处：调用方经_ring_correct_near_x传入竖线列，
            # 仅保留其±25px内的圆环run、只改写±15px内路径点；未设置时
            # (电价等面板)保持全量圆环校正。
            ring_near = getattr(self, "_ring_correct_near_x", None)
            if ring_near is not None:
                ring_runs = [r for r in ring_runs
                             if abs(r[0] - ring_near) <= 25]

            def _ring_expected(c):
                if not ring_runs:
                    return None
                if c <= ring_runs[0][0]:
                    return ring_runs[0][1] if c >= ring_runs[0][0] - 10 else None
                if c >= ring_runs[-1][0]:
                    return ring_runs[-1][1] if c <= ring_runs[-1][0] + 10 else None
                for k in range(len(ring_runs) - 1):
                    c0, m0 = ring_runs[k]
                    c1, m1 = ring_runs[k + 1]
                    if c0 <= c <= c1:
                        return m0 + (m1 - m0) * (c - c0) / max(c1 - c0, 1e-6)
                return None

            path = [(xx, (exp if (exp is not None and abs(yy - exp) > 1.5 and
                                  (ring_near is None or
                                   abs(xx - ring_near) <= 15)) else yy))
                    for xx, yy in path for exp in [_ring_expected(xx)]]
            points = [(xx, int(round(yy))) for xx, yy in path]

        # 注：DP路径追踪已具备抗噪能力，不再做medfilt（会削掉真实尖峰的顶端，
        # 如实时电价715.93的尖峰被削成655）

        points = self._deduplicate_and_sort(points)

        # ==================== V4.6：碎片接续（骨干两端贪心延伸） ====================
        # 大组件构成的骨干路径只覆盖线条的强色段；被填充洗淡的线段碎成
        # 小组件已在上面被过滤，导致曲线末端被插值钳成恒值（05-02三个
        # 出力面板的实时出力13:15后全部冻结）。这里沿骨干两端用完整掩码
        # 贪心接续：每列取距当前行±25px内最近的簇顶（与DP候选定义一致），
        # 允许≤40列空档（抗网格线/标记造成的掩码断口）。
        # 标注文字紧贴曲线峰值、位于骨干覆盖段内，延伸区（骨干两端之外）
        # 无文字，±25px行窗进一步保证不会跳到文字上。
        if len(points) >= 2 and cx1 > cx0:
            # V4.6b：延伸优先用开运算前的原始掩码（2px细线被开运算腐蚀，
            # 原始掩码+闭运算补桥后可找回）；行窗随空档自适应放大
            # 25+1.2*gap（实测32列断口线位移21px），空档容忍60列。
            frag_src = None
            raw_masks = getattr(self, "_raw_color_masks", None)
            if raw_masks is not None:
                frag_src = raw_masks.get(color_name)
            if frag_src is None or frag_src.shape != mask.shape:
                frag_src = mask_unfiltered
            else:
                frag_src = cv2.morphologyEx(
                    frag_src, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
                fclip = np.zeros_like(frag_src)
                fclip[cy0:cy1, cx0:cx1] = frag_src[cy0:cy1, cx0:cx1]
                frag_src = fclip
                self._erase_plot_text(frag_src, cx0, cx1, cy0, cy1)
            frag_rows = {}
            fys, fxs = np.where(frag_src > 0)
            for xx, yy in zip(fxs, fys):
                frag_rows.setdefault(xx, []).append(yy)

            def _nearest_cluster_top(xx, cur_y, win):
                rows = frag_rows.get(xx)
                if not rows:
                    return None
                rows = sorted(rows)
                clusters, cur = [], [rows[0]]
                for r in rows[1:]:
                    if r - cur[-1] <= 6:
                        cur.append(r)
                    else:
                        clusters.append(cur)
                        cur = [r]
                clusters.append(cur)
                tops = [float(min(c)) + 1.0 for c in clusters]
                best = min(tops, key=lambda t: abs(t - cur_y))
                return best if abs(best - cur_y) <= win else None

            ext_right = []
            cur_y = float(points[-1][1])
            gap = 0
            for xx in range(points[-1][0] + 1, cx1):
                top = _nearest_cluster_top(xx, cur_y, 25 + 1.2 * gap)
                if top is None:
                    gap += 1
                    if gap > 60:
                        break
                    continue
                ext_right.append((xx, top))
                cur_y = top
                gap = 0

            ext_left = []
            cur_y = float(points[0][1])
            gap = 0
            for xx in range(points[0][0] - 1, cx0 - 1, -1):
                top = _nearest_cluster_top(xx, cur_y, 25 + 1.2 * gap)
                if top is None:
                    gap += 1
                    if gap > 60:
                        break
                    continue
                ext_left.append((xx, top))
                cur_y = top
                gap = 0

            if ext_right or ext_left:
                print(f"[INFO] {color_name}碎片接续: 骨干{points[0][0]}-{points[-1][0]}"
                      f" 左延{len(ext_left)}列 右延{len(ext_right)}列")
                points = self._deduplicate_and_sort(
                    [(xx, int(round(yy))) for xx, yy in
                     (ext_left[::-1] + list(points) + ext_right)])

        curve = CurveData(name=f"{color_name}_曲线", color_name=color_name)
        curve.pixel_points = points
        curve.points = self._pixel_to_real(points, axis)
        curve.confidence = 0.7
        curve._axis = axis  # V4.3：坐标轴随曲线绑定，插值不再受全局陈旧轴污染

        return curve

    def _deduplicate_and_sort(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """去重并按X排序"""
        seen = set()
        unique = []
        for x, y in points:
            if x not in seen:
                seen.add(x)
                unique.append((x, y))
        unique.sort(key=lambda p: p[0])
        return unique

    def _pixel_to_real(self, pixel_points: List[Tuple[int, int]], axis: AxisInfo) -> List[Tuple[float, float]]:
        """将像素坐标转换为实际数值（自动叠加面板裁剪偏移）"""
        real_points = []

        ox, oy = getattr(self, "_px_offset", (0, 0))

        x_px_min, x_px_max = axis.x_pixel_range
        y_px_min, y_px_max = axis.y_pixel_range

        x_real_min, x_real_max = axis.x_min, axis.x_max
        y_real_min, y_real_max = axis.y_min, axis.y_max

        for px, py in pixel_points:
            px_a, py_a = px + ox, py + oy  # 裁剪相对坐标 -> 全图绝对坐标

            # X映射（线性）
            if x_px_max != x_px_min:
                x_real = x_real_min + (px_a - x_px_min) / (x_px_max - x_px_min) * (x_real_max - x_real_min)
            else:
                x_real = x_real_min

            # Y映射（注意Y轴像素通常从上到下递增，而实际值从下到上递增）
            if y_px_max != y_px_min:
                y_real = y_real_min + (y_px_max - py_a) / (y_px_max - y_px_min) * (y_real_max - y_real_min)
            else:
                y_real = y_real_min

            real_points.append((x_real, y_real))

        return real_points

    # --------------------------------------------------------------------------
    # 步骤5: 数据插值与平滑
    # --------------------------------------------------------------------------
    def interpolate_to_96points(self, curve: CurveData) -> CurveData:
        """
        将曲线插值为96点（15分钟间隔）

        策略：
        1. 使用原始数据点
        2. 在0-24小时范围内均匀采样96点
        3. 使用样条插值
        4. Savitzky-Golay平滑
        """
        if not curve.points or len(curve.points) < 4:
            curve.is_valid = False
            curve.error_msg = "数据点不足，无法插值"
            return curve

        points = np.array(curve.points)
        x_raw = points[:, 0]
        y_raw = points[:, 1]

        # 确保X单调递增
        sort_idx = np.argsort(x_raw)
        x_raw = x_raw[sort_idx]
        y_raw = y_raw[sort_idx]

        # 去重X值
        x_unique, idx = np.unique(x_raw, return_index=True)
        y_unique = y_raw[idx]

        if len(x_unique) < 4:
            curve.is_valid = False
            curve.error_msg = "唯一数据点不足，无法插值"
            return curve

        # 生成96个均匀分布的点（0-24小时，15分钟间隔）
        n_points = self.config["chart"]["output_points"]
        # 96个时点从 00:15 开始到 24:00（电力现货市场96点标准：0.25h~24.00h）
        x_target = (np.arange(n_points) + 1) * (24.0 / n_points)

        # 插值：优先PCHIP保形插值（单调无振荡，跨数据空档走线性，
        # 不会像CubicSpline那样在空档甩出假谷/假峰；阶梯处也不过冲）
        try:
            if len(x_unique) >= 3:
                from scipy.interpolate import PchipInterpolator
                y_interp = PchipInterpolator(x_unique, y_unique)(x_target)
            else:
                y_interp = np.interp(x_target, x_unique, y_unique)
        except Exception:
            y_interp = np.interp(x_target, x_unique, y_unique)

        # 边缘保持：数据范围外不外推（光伏夜间无数据段会被样条外推后
        # 被clip钉死在轴上限，形成假平台；改为保持端点值，夜间自然归0）
        y_interp[x_target < x_unique[0]] = y_unique[0]
        y_interp[x_target > x_unique[-1]] = y_unique[-1]

        # 太阳能面板特化：夜间本来就无数据且无发电，缺数段直接填0
        if getattr(self, "_zero_fill_gap", False):
            y_interp[x_target < x_unique[0]] = 0.0
            y_interp[x_target > x_unique[-1]] = 0.0

        # Savitzky-Golay平滑（电价曲线禁用：现货电价是阶梯函数，平滑会破坏台阶；
        # 负荷虚线可逐曲线设置更轻窗口，避免15分钟峰值被整体压低/搬移）
        window = min(getattr(curve, "_smooth_window",
                             self.config["chart"]["smoothing_window"]),
                     len(y_interp)//2*2+1)
        if getattr(self, "_no_smooth", False) or getattr(curve, "_no_smooth", False):
            window = 0
        if window >= 5:
            try:
                y_smooth = savgol_filter(y_interp, window,
                                        self.config["chart"]["smoothing_polyorder"])
            except Exception:
                y_smooth = y_interp
        else:
            y_smooth = y_interp

        # 裁剪到Y轴标定范围（防止样条插值过冲出图表边界）
        # V4.3根因修复：优先使用曲线自带的坐标轴（提取时绑定），
        # 避免self._last_axis被上一面板（如风电Y=[1989,14000]）污染，
        # 导致负荷曲线37000~84000被clip成14000常数直线。
        axis = getattr(curve, "_axis", None) or getattr(self, "_last_axis", None)
        if axis is not None:
            lo = min(axis.y_min, axis.y_max)
            hi = max(axis.y_min, axis.y_max)
            y_smooth = np.clip(y_smooth, lo, hi)

        # 更新曲线数据
        curve.points = list(zip(x_target, y_smooth))
        curve.confidence = min(1.0, curve.confidence + 0.1)

        return curve

    # --------------------------------------------------------------------------
    # 步骤6: 结果验证
    # --------------------------------------------------------------------------
    def validate_result(self, result: ExtractionResult) -> ExtractionResult:
        """验证提取结果"""
        warnings_list = []

        for curve in result.curves:
            if not curve.is_valid:
                continue

            y_values = [p[1] for p in curve.points]

            # 检查数值范围（以坐标轴标定范围为基准，上下放宽30%）
            axis = result.axis_info
            if axis and axis.y_max > axis.y_min:
                span = axis.y_max - axis.y_min
                max_val = axis.y_max + 0.3 * span
                min_val = axis.y_min - 0.3 * span
            else:
                max_val = self.config["validation"]["max_price"]
                min_val = self.config["validation"]["min_price"]

            if max(y_values) > max_val:
                warnings_list.append(f"{curve.name}: 最大值 {max(y_values):.2f} 超出合理范围")
                curve.confidence *= 0.8

            if min(y_values) < min_val:
                warnings_list.append(f"{curve.name}: 最小值 {min(y_values):.2f} 超出合理范围")
                curve.confidence *= 0.8

            # 检查连续性（跳变检测）
            jumps = []
            for i in range(1, len(y_values)):
                if y_values[i-1] != 0:
                    relative_jump = abs(y_values[i] - y_values[i-1]) / abs(y_values[i-1] + 1e-6)
                    if relative_jump > self.config["validation"]["continuity_threshold"] * 5:
                        jumps.append(i)

            if len(jumps) > 5:
                warnings_list.append(f"{curve.name}: 检测到 {len(jumps)} 处异常跳变，建议人工校验")
                curve.confidence *= 0.9

        # 警告去重 + 限量（避免刷屏）
        seen = set()
        unique_warnings = []
        for msg in warnings_list:
            if msg not in seen:
                seen.add(msg)
                unique_warnings.append(msg)
        if len(unique_warnings) > 10:
            omitted = len(unique_warnings) - 10
            unique_warnings = unique_warnings[:10]
            unique_warnings.append(f"... 其余 {omitted} 条警告已省略")
        result.warnings = unique_warnings
        result.confidence = np.mean([c.confidence for c in result.curves if c.is_valid]) if result.curves else 0.0

        return result

    # --------------------------------------------------------------------------
    # 步骤7: 输出CSV
    # --------------------------------------------------------------------------
    def export_to_csv(self, result: ExtractionResult, output_path: str) -> str:
        """导出结果为CSV"""
        if not result.curves:
            print("[WARN] 无曲线数据可导出")
            return ""

        # 构建DataFrame
        n_points = self.config["chart"]["output_points"]

        # 时间列（96点，15分钟间隔）
        # 96点时间标签：00:15 起步，24:00 收尾（现货市场96点标准）
        times = []
        for i in range(1, 97):
            total_min = i * 15
            hh, mm = total_min // 60, total_min % 60
            times.append("24:00" if hh == 24 else f"{hh:02d}:{mm:02d}")

        data = {"时点": list(range(1, n_points + 1)), "时间": times}

        for curve in result.curves:
            if curve.is_valid and len(curve.points) == n_points:
                col_name = curve.name
                data[col_name] = [round(p[1], 2) for p in curve.points]

        df = pd.DataFrame(data)

        # 保存CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        result.output_csv = output_path

        print(f"[INFO] CSV已保存: {output_path}")
        print(f"[INFO] 数据预览（前5行）:")
        print(df.head().to_string(index=False))

        return output_path

    def export_to_json(self, result: ExtractionResult, output_path: str) -> str:
        """导出完整结果为JSON（含元数据）"""
        export_data = {
            "metadata": {
                "image_path": result.image_path,
                "extraction_time": datetime.now().isoformat(),
                "chart_roi": result.chart_roi,
                "confidence": result.confidence,
                "warnings": result.warnings,
            },
            "axis_info": asdict(result.axis_info),
            "curves": [
                {
                    "name": c.name,
                    "color": c.color_name,
                    "confidence": c.confidence,
                    "is_valid": c.is_valid,
                    "error_msg": c.error_msg,
                    "points": [{"x": round(p[0], 4), "y": round(p[1], 2)} for p in c.points]
                }
                for c in result.curves
            ],
            "raw_text": result.text_data
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"[INFO] JSON已保存: {output_path}")
        return output_path

    # --------------------------------------------------------------------------
    # 调试可视化
    # --------------------------------------------------------------------------
    def visualize(self, img: np.ndarray, result: ExtractionResult, output_path: str):
        """生成可视化调试图"""
        if not MPL_AVAILABLE:
            print("[WARN] matplotlib未安装，跳过可视化")
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 原图+ROI
        ax1 = axes[0, 0]
        ax1.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        x, y, w, h = result.chart_roi
        rect = plt.Rectangle((x, y), w, h, fill=False, edgecolor='red', linewidth=2)
        ax1.add_patch(rect)
        ax1.set_title("图表ROI检测")
        ax1.axis('off')

        # OCR文字标注
        ax2 = axes[0, 1]
        roi_img = img[y:y+h, x:x+w]
        ax2.imshow(cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB))
        for t in result.text_data[:20]:  # 只显示前20个
            ax2.text(t["center_x"]-x, t["center_y"]-y, t["text"], 
                    fontsize=8, color='yellow', bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        ax2.set_title("OCR识别结果")
        ax2.axis('off')

        # 曲线提取
        ax3 = axes[1, 0]
        ax3.imshow(cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB))
        for curve in result.curves:
            if curve.pixel_points:
                px = [p[0] for p in curve.pixel_points]
                py = [p[1] for p in curve.pixel_points]
                ax3.plot(px, py, linewidth=2, label=curve.name)
        ax3.set_title("曲线追踪")
        ax3.legend(fontsize=8)
        ax3.axis('off')

        # 插值结果
        ax4 = axes[1, 1]
        for curve in result.curves:
            if curve.is_valid and curve.points:
                x_vals = [p[0] for p in curve.points]
                y_vals = [p[1] for p in curve.points]
                ax4.plot(x_vals, y_vals, marker='o', markersize=2, linewidth=1, label=curve.name)
        ax4.set_xlabel("时间 (小时)")
        ax4.set_ylabel(result.axis_info.y_unit or "数值")
        ax4.set_title("96点插值结果")
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"[INFO] 可视化图已保存: {output_path}")

    # --------------------------------------------------------------------------
    # 多面板检测（山东电力交易中心Dashboard多窗口截图）
    # --------------------------------------------------------------------------
    def detect_panels(self, img: np.ndarray, texts: List[Dict]) -> List[Dict]:
        """
        检测截图中的各个图表面板（V2 标题锚定法）：
        相邻白色卡片常粘连成一张大卡，改为以标题位置为锚：
        1. 标题（市场出清/负荷及出力/出清信息）必然位于各自卡片左上角
        2. 面板左/上边界 = 标题位置外扩；右边界 = 同行下一标题的左缘（或白卡右缘）
        3. 面板内文本判断子类型（电价/电量/出力类型）与日期
        """
        H, W = img.shape[:2]

        # ---- 1) 标题文本定位（含bbox边缘坐标） ----
        titles = []
        for t in texts:
            for key, ptype in PANEL_TITLE_MAP:
                if key in t["text"]:
                    xs = [p[0] for p in t["bbox"]]
                    ys = [p[1] for p in t["bbox"]]
                    titles.append({"text": t["text"], "type": ptype,
                                   "cx": t["center_x"], "cy": t["center_y"],
                                   "left": min(xs), "top": min(ys)})
                    break

        if not titles:
            # 极端情况：所有标题OCR失败时，仍尝试用负荷图例兜底
            load_only = self._detect_load_panel_fallback(img, texts)
            return [load_only] if load_only else []

        # ---- 2) 白色卡片检测（仅用于确定下/右边界） ----
        white = cv2.inRange(img, (238, 238, 238), (255, 255, 255))
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, k)
        contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cards = []
        for c in contours:
            bx, by, bw, bh = cv2.boundingRect(c)
            if bw > 300 and bh > 250 and bw * bh > 0.01 * W * H:
                cards.append((bx, by, bw, bh))

        # ---- 3) 逐标题构建面板矩形 ----
        panels = []
        for ti in titles:
            left = max(0, int(ti["left"]) - 18)
            top = max(0, int(ti["top"]) - 12)

            # 右边界：同一行（标题顶部接近）右侧最近标题的左缘
            right = W
            for tj in titles:
                if tj is ti:
                    continue
                if abs(tj["top"] - ti["top"]) < 60 and tj["left"] > ti["left"] + 50:
                    right = min(right, int(tj["left"]) - 25)

            # 下/右边界：所属白卡
            bottom = None
            for (bx, by, bw, bh) in cards:
                if bx - 15 <= ti["cx"] <= bx + bw + 15 and by - 15 <= ti["cy"] <= by + bh + 15:
                    bottom = by + bh
                    right = min(right, bx + bw)
                    break
            if bottom is None:
                bottom = min(H, top + 470)
            right = min(right, W)

            w = max(200, right - left)
            h = max(200, bottom - top)
            rect = (left, top, w, h)

            # ---- 4) 面板内文本：子类型 + 日期 ----
            inner = [t for t in texts
                     if left <= t["center_x"] <= left + w and top <= t["center_y"] <= top + h]
            joined = " ".join(t["text"] for t in inner)

            subtype = ti["type"]
            if ti["type"] == "clearing":
                subtype = "price" if ("元/MWh" in joined or "元 /MWh" in joined) else "energy"
            elif ti["type"] == "load":
                for opt in ["太阳能发电", "风电", "非市场化机组", "全网发电", "全社会用电"]:
                    if opt in joined:
                        subtype = f"load_{opt}"
                        break

            m = re.search(r'(20\d{2})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})', joined)
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else "unknown"

            panels.append({"title": ti["text"], "type": ti["type"], "subtype": subtype,
                           "date": date, "slug": f"{subtype}_{date}", "rect": rect})

        # ---- 5) 负荷面板兜底检测（标题被tooltip遮挡时仍可识别） ----
        # 2026-05-01截图中，底部负荷面板标题被深色悬浮框盖住，OCR可能读不到
        # “负荷及出力”标题；但右侧图例“预测/实际直调负荷、预测/实际全网负荷”
        # 与底部时间刻度仍完整可见。用图例锚定面板，避免4列负荷整组缺失。
        load_fb = self._detect_load_panel_fallback(img, texts)
        if load_fb:
            idx = next((i for i, p in enumerate(panels) if p.get("subtype") == "load"), None)
            if idx is None:
                panels.append(load_fb)
                print(f"[INFO] 负荷面板标题兜底识别成功: rect={load_fb['rect']}")
            elif not self._panel_axis_plausible(panels[idx], texts):
                print(f"[WARN] 原负荷面板坐标轴证据不足，改用图例兜底矩形: "
                      f"old={panels[idx]['rect']} new={load_fb['rect']}")
                panels[idx] = load_fb

        # ---- 6) 同slug去重（截图常有重复面板） ----
        uniq = {}
        for p in panels:
            # 同一slug出现多次时，优先保留坐标轴证据更充分的矩形
            old = uniq.get(p["slug"])
            if old is None or self._panel_axis_score(p, texts) > self._panel_axis_score(old, texts):
                uniq[p["slug"]] = p
        panels = list(uniq.values())

        for p in panels:
            print(f"[INFO] 面板: {p['slug']} | {p['title']} | rect={p['rect']}")
        return panels

    def _panel_axis_score(self, panel: Dict, texts: List[Dict]) -> int:
        """面板内坐标轴证据评分：底部时间刻度数 + 左侧数值刻度数。"""
        x, y, w, h = panel["rect"]
        inner = [t for t in texts
                 if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h]
        x_score = 0
        for t in inner:
            if t["center_y"] >= y + h * 0.72:
                x_score += len(re.findall(r'\d{1,2}\s*[:：]\s*\d{2}', t["text"]))
        y_score = len([t for t in inner
                       if t.get("numeric_value") is not None
                       and t["center_x"] <= x + w * 0.18
                       and y + h * 0.15 <= t["center_y"] <= y + h * 0.95])
        return min(x_score, 8) + min(y_score, 8)

    def _panel_axis_plausible(self, panel: Dict, texts: List[Dict]) -> bool:
        """至少3个X时间刻度 + 2个Y数值刻度，才认为面板矩形可用于标定。"""
        return self._panel_axis_score(panel, texts) >= 5

    def _detect_load_panel_fallback(self, img: np.ndarray, texts: List[Dict]) -> Optional[Dict]:
        """
        负荷面板OCR标题缺失时的几何兜底检测。

        依据（该Dashboard固定布局）：
        - 右侧图例含“直调负荷/全网负荷”，tooltip中的同名行必带冒号，先排除；
        - 底部X轴为 00:15、03:30、06:45...23:00；
        - 左侧Y轴为 0、20,000...100,000。
        通过图例锚点向下找时间刻度行，再向左找数值刻度列，反推出完整面板矩形。
        """
        def _bbox_left(t): return min(p[0] for p in t["bbox"])
        def _bbox_right(t): return max(p[0] for p in t["bbox"])
        def _bbox_top(t): return min(p[1] for p in t["bbox"])
        def _bbox_bottom(t): return max(p[1] for p in t["bbox"])

        legend = []
        for t in texts:
            txt = t["text"]
            # tooltip行形如“预测直调负荷: 40,347.87”，不是图例
            if ':' in txt or '：' in txt:
                continue
            if ("直调负荷" in txt or "全网负荷" in txt):
                legend.append(t)
        if not legend:
            return None

        joined = " ".join(t["text"] for t in legend)
        if "直调负荷" not in joined or "全网负荷" not in joined:
            return None

        # 取最靠下的图例簇（底部负荷面板）；tooltip同名行已因冒号被排除
        anchor_y = max(t["center_y"] for t in legend)
        anchors = [t for t in legend if abs(t["center_y"] - anchor_y) <= 60]
        a_left = min(_bbox_left(t) for t in anchors)
        a_right = max(_bbox_right(t) for t in anchors)
        a_top = min(_bbox_top(t) for t in anchors)

        # 找图例下方的时间刻度行。兼容两种OCR结果：
        # 1) 每个刻度独立一条；2) 整行被合并成“00:15 03:30 ...”一条。
        row_groups = {}
        for t in texts:
            if t["center_y"] <= anchor_y + 70:
                continue
            matches = list(re.finditer(r'\d{1,2}\s*[:：]\s*\d{2}', t["text"]))
            if not matches:
                continue
            # 必须在图例附近水平延展范围内，排除其它面板
            if _bbox_right(t) < a_left - 650 or _bbox_left(t) > a_right + 120:
                continue
            key = int(round(t["center_y"] / 12.0) * 12)
            row_groups.setdefault(key, []).append((t, len(matches)))

        best_row = None
        best_key = None
        for key, items in row_groups.items():
            tick_count = sum(n for _, n in items)
            row_y = max(t["center_y"] for t, _ in items)
            # 优先刻度数量，其次更靠下的行
            cand = (tick_count, row_y)
            if best_row is None or cand > best_row:
                best_row = cand
                best_key = key
        if not best_row or best_row[0] < 3:
            return None

        x_items = [t for t, _ in row_groups[best_key]]
        x_left = min(_bbox_left(t) for t in x_items)
        x_right = max(_bbox_right(t) for t in x_items)
        x_bottom = max(_bbox_bottom(t) for t in x_items)

        # 左侧Y轴数值刻度：位于第一时间标签左侧，0~200000 MW
        y_ticks = []
        for t in texts:
            v = t.get("numeric_value")
            if v is None or not (0 <= v <= 200000):
                continue
            if not (anchor_y - 20 <= t["center_y"] <= x_bottom + 10):
                continue
            if t["center_x"] < x_left - 3:
                y_ticks.append(t)
        if len(y_ticks) < 2:
            return None

        left = max(0, int(min(x_left - 85, min(_bbox_left(t) for t in y_ticks) - 12)))
        right = min(img.shape[1], int(max(x_right + 80, a_right + 20)))
        top = max(0, int(min(a_top - 55, min(_bbox_top(t) for t in y_ticks) - 25)))
        bottom = min(img.shape[0], int(x_bottom + 35))
        rect = (left, top, max(200, right - left), max(200, bottom - top))

        inner = [t for t in texts
                 if left <= t["center_x"] <= left + rect[2]
                 and top <= t["center_y"] <= top + rect[3]]
        joined_inner = " ".join(t["text"] for t in inner)
        m = re.search(r'(20\d{2})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})', joined_inner)
        if m:
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        else:
            # 兜底矩形通常从图例顶部开始，未必包含右上角日期；
            # 取全图OCR中出现次数最多的日期（Dashboard所有面板同日）。
            from collections import Counter
            all_dates = []
            for t in texts:
                for mm in re.finditer(r'(20\d{2})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})',
                                      t["text"]):
                    all_dates.append(f"{mm.group(1)}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}")
            date = Counter(all_dates).most_common(1)[0][0] if all_dates else "unknown"

        return {"title": "预测/实际负荷及出力(图例兜底)", "type": "load",
                "subtype": "load", "date": date,
                "slug": f"load_{date}", "rect": rect,
                "legend_boxes": [t["bbox"] for t in anchors]}

    def _find_curve_peak_marker(self, img: np.ndarray, panel: Dict,
                                axis: AxisInfo, curve: CurveData) -> Optional[Dict]:
        """
        定位曲线“当日峰值”的空心圆点中心。

        V3.6用峰值标注文字左缘估算时间；但Dashboard常把文字放在圆点左/右/下方，
        导致吸附时点偏移。这里改为：同色系HSV掩码 → Hough空心圆检测 →
        与原始曲线路径做距离门控 → 取像素反算值最高（同值取最早）的圆点。
        返回 {value, time, cx, cy, radius}；找不到时返回None并走旧逻辑兜底。
        """
        if not curve.pixel_points or curve.color_name.startswith("load_"):
            return None

        color_ranges = {
            "red": [((0, 45, 70), (8, 255, 255)), ((170, 45, 70), (179, 255, 255))],
            "orange": [((9, 45, 70), (34, 255, 255))],
            "yellow": [((12, 45, 70), (34, 255, 255))],
            "green": [((45, 35, 60), (85, 255, 255))],
            "cyan": [((80, 35, 60), (95, 255, 255))],
            "blue": [((95, 35, 60), (125, 255, 255))],
            "purple": [((126, 35, 60), (165, 255, 255))],
        }
        ranges = color_ranges.get(curve.color_name)
        if not ranges:
            return None

        x, y, w, h = panel["rect"]
        roi = img[y:y + h, x:x + w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                                np.array(hi, dtype=np.uint8))

        # 只保留绘图区，排除图例与标题区圆点
        ox, oy = x, y
        self._px_offset = (ox, oy)
        x0a, x1a = axis.x_pixel_range
        y0a, y1a = axis.y_pixel_range
        xspan = abs(x1a - x0a)
        rx0 = max(0, int(min(x0a, x1a) - ox - xspan * 0.02))
        rx1 = min(mask.shape[1], int(max(x0a, x1a) - ox + xspan * 0.04))
        ry0 = max(0, int(min(y0a, y1a) - oy - 12))
        ry1 = min(mask.shape[0], int(max(y0a, y1a) - oy + 12))
        clipped = np.zeros_like(mask)
        if rx1 > rx0 and ry1 > ry0:
            clipped[ry0:ry1, rx0:rx1] = mask[ry0:ry1, rx0:rx1]
        mask = clipped

        # 轻微闭运算补圆环断口；多阈值候选合并评分，不能只取第一个命中阈值
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        circle_list = []
        for p2 in (8, 6, 5):
            cs = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, dp=1,
                                  minDist=8, param1=45, param2=p2,
                                  minRadius=5, maxRadius=15)
            if cs is not None and len(cs[0]) > 0:
                circle_list.extend(cs[0].tolist())
        if not circle_list:
            return None

        path = {}
        for px, py in curve.pixel_points:
            path.setdefault(int(px), []).append(float(py))
        span_v = axis.y_max - axis.y_min
        candidates = []
        for cx_f, cy_f, r_f in circle_list:
            cx, cy, rr = int(round(cx_f)), int(round(cy_f)), float(r_f)
            # 必须落在绘图区（允许少量标定误差）
            if not (rx0 - 4 <= cx <= rx1 + 4 and ry0 - 4 <= cy <= ry1 + 4):
                continue

            # 与曲线路径的距离门控：排除图例/文字0、6、8、9形成的假圆
            nearby = []
            for xx in range(cx - 4, cx + 5):
                nearby.extend(path.get(xx, []))
            if nearby:
                path_dist = min(abs(cy - yy) for yy in nearby)
                if path_dist > 35:
                    continue
            else:
                continue

            try:
                t_val, y_val = self._pixel_to_real([(cx, cy)], axis)[0]
            except Exception:
                continue
            if y_val < axis.y_min - 0.03 * span_v or y_val > axis.y_max + 0.03 * span_v:
                continue
            candidates.append({"value": float(y_val), "time": float(t_val),
                               "cx": cx, "cy": cy, "radius": rr,
                               "path_dist": float(path_dist)})
        if not candidates:
            return None

        # 峰值圆点=像素反算值最高；平台线同值时取最早圆点（如13941.00@00:15）
        best = max(candidates, key=lambda c: (c["value"], -c["cx"], -c["path_dist"]))
        print(f"[DEBUG] 峰值圆点定位: {curve.name} -> {best['value']:.2f} @ "
              f"{best['time']:.2f}h (px={best['cx']},{best['cy']}, r={best['radius']:.1f})")
        return best

    def _find_annotation_marker(self, img: np.ndarray, panel: Dict,
                                axis: AxisInfo, curve: CurveData,
                                annotation: Dict) -> Optional[Dict]:
        """
        按“标注值对应的Y像素”定位其同色空心圆点。

        与_find_curve_peak_marker不同，这里以OCR标注值v为Y锚点：
        文字中的0/6/8/9虽也会形成假圆，但其圆心Y通常不等于v的轴标定位置，
        会被±容差过滤。用于最终吸附时刻，尤其可修复538.50/15618.55/
        43647.98等“文字左缘时间”偏差。
        """
        color_ranges = {
            "red": [((0, 45, 70), (8, 255, 255)), ((170, 45, 70), (179, 255, 255))],
            "orange": [((9, 45, 70), (34, 255, 255))],
            "yellow": [((12, 45, 70), (34, 255, 255))],
            "green": [((45, 35, 60), (85, 255, 255))],
            "cyan": [((80, 35, 60), (95, 255, 255))],
            "blue": [((95, 35, 60), (125, 255, 255))],
            "purple": [((126, 35, 60), (165, 255, 255))],
        }
        ranges = color_ranges.get(curve.color_name)
        if not ranges:
            return None

        x, y, w, h = panel["rect"]
        roi = img[y:y + h, x:x + w]
        self._px_offset = (x, y)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                                np.array(hi, dtype=np.uint8))

        x0a, x1a = axis.x_pixel_range
        y0a, y1a = axis.y_pixel_range
        span_v = axis.y_max - axis.y_min
        if span_v <= 0:
            return None
        v = float(annotation["v"])
        # 标注值 -> 期望圆心Y（面板相对坐标）
        py_exp = (max(y0a, y1a)
                  - (v - axis.y_min) / span_v * (max(y0a, y1a) - min(y0a, y1a))) - y
        ytol = max(14.0, abs(y1a - y0a) * 0.06)
        xspan = abs(x1a - x0a)
        rx0 = max(0, int(min(x0a, x1a) - x - xspan * 0.02))
        rx1 = min(mask.shape[1], int(max(x0a, x1a) - x + xspan * 0.04))
        ry0 = max(0, int(py_exp - ytol - 8))
        ry1 = min(mask.shape[0], int(py_exp + ytol + 8))
        if rx1 <= rx0 or ry1 <= ry0:
            return None

        clipped = np.zeros_like(mask)
        clipped[ry0:ry1, rx0:rx1] = mask[ry0:ry1, rx0:rx1]
        clipped = cv2.morphologyEx(clipped, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        circle_list = []
        for p2 in (8, 6, 5, 4):
            cs = cv2.HoughCircles(clipped, cv2.HOUGH_GRADIENT, dp=1,
                                  minDist=7, param1=40, param2=p2,
                                  minRadius=4, maxRadius=15)
            if cs is not None and len(cs[0]) > 0:
                circle_list.extend(cs[0].tolist())
        if not circle_list:
            return None

        bbox = annotation.get("bbox")
        path_map = {}
        for px, py in curve.pixel_points:
            path_map.setdefault(int(px), []).append(float(py))
        candidates = []
        for cx_f, cy_f, rr_f in circle_list:
            cx, cy, rr = int(round(cx_f)), int(round(cy_f)), float(rr_f)
            if abs(cy - py_exp) > ytol:
                continue
            if bbox:
                bx0, by0, bx1, by1 = bbox
                # bbox是全图坐标；圆点在标注左右120px内（标签常左右偏移）
                cx_abs, cy_abs = cx + x, cy + y
                xdist = 0.0 if bx0 - 20 <= cx_abs <= bx1 + 20 else min(
                    abs(cx_abs - bx0), abs(cx_abs - bx1))
                if xdist > 140:
                    continue
            else:
                xdist = 0.0
            try:
                t_val, y_val = self._pixel_to_real([(cx, cy)], axis)[0]
            except Exception:
                continue
            near_path = []
            for xx in range(cx - 4, cx + 5):
                near_path.extend(path_map.get(xx, []))
            path_dist = min((abs(cy - yy) for yy in near_path), default=None)
            if path_dist is not None and path_dist > 35:
                continue

            px_per_hour = max(abs(x1a - x0a) / max(axis.x_max - axis.x_min, 1e-6), 1.0)
            time_penalty = abs(t_val - float(annotation.get("t", t_val))) * px_per_hour * 0.35
            # 在±Y容差内，真正峰值圆点通常贴近同色曲线；
            # 文字假圆即使更靠上，也会因离曲线路径较远而失分。
            score = (cy * 1.0 + xdist * 0.05 +
                     abs(rr - 9.0) * 0.5 + time_penalty * 0.10 +
                     (path_dist if path_dist is not None else 15.0) * 2.0)
            candidates.append({"time": float(t_val), "value": float(y_val),
                               "cx": cx, "cy": cy, "radius": rr,
                               "score": float(score)})
        if not candidates:
            return None
        best = min(candidates, key=lambda c: c["score"])
        print(f"[DEBUG] 标注圆点定位: {curve.name} 标注{v:.2f} -> "
              f"{best['time']:.2f}h (期望Y={py_exp:.1f}, 实际Y={best['cy']})")
        return best

    def _targeted_peak_ocr(self, img: np.ndarray, panel: Dict, axis: AxisInfo,
                           curve: CurveData, gmax: float, t_pk: float,
                           fam: Optional[str], v_lo: float, v_hi: float) -> Optional[Dict]:
        """
        定点二次OCR（V3.6）：全图OCR漏读/熔读的峰值标注定向识别。
        适用：橙字压橙线小数点被吞、蓝字与Y轴刻度熔合（如'14,020173.47'）等
        全图OCR无法产出该曲线标注候选的情形。
        原理：按轴标定把曲线峰值换算回像素位置，裁剪全轴宽横条（峰上下±45px，
        标注水平位置可能被钳位到面板边缘，故取全宽），目标色系像素隔离
        （目标色→黑、其余→白，灰色刻度/异色标注/白tooltip字全被滤除）+4x放大，
        复用OCR引擎识别。
        安全设计（宁可跳过、不可错绑）：
          - 不做曲线减除（文字与曲线同色同掩码，减除会连文字一起擦掉）；
          - 候选文字patch在原图上必须检出同色系彩色像素（防误收邻曲线异色
            标注或灰色刻度，如全网面板蓝色68316.00被橙曲线误收）；
          - 候选与曲线当前峰值差>=12%拒绝（V3.5圆环校正后gmax已接近真值，
            大偏差说明是OCR误读而非曲线污染）。
        返回注入分配管线的候选dict（curve_ci由调用方绑定），失败返回None。
        """
        x, y, w, h = panel["rect"]
        x0p, x1p = axis.x_pixel_range
        y0p, y1p = axis.y_pixel_range
        span_v = axis.y_max - axis.y_min
        H, W = img.shape[:2]
        COLOR_FAMILY_T = {"red": "warm", "orange": "warm", "yellow": "warm",
                          "green": "green", "cyan": "green",
                          "blue": "blue", "purple": "blue"}

        # 峰值像素 -> 裁剪横条（全轴宽，峰值上下±45px）
        py = y1p - (gmax - axis.y_min) / span_v * (y1p - y0p)
        sx0 = int(max(min(x0p, x1p) - 60, x, 0))
        sx1 = int(min(max(x0p, x1p) + 10, x + w, W))
        sy0 = int(max(py - 45, y, 0))
        sy1 = int(min(py + 45, y + h, H))
        if sx1 - sx0 < 40 or sy1 - sy0 < 20:
            return None
        strip = img[sy0:sy1, sx0:sx1]

        def parse_vals(raw):
            raw = raw.replace(' ', '').replace(',', '').replace('，', '').replace('．', '.')
            out = []
            if '.' in raw:
                if re.fullmatch(r'\d+\.\d{2}', raw):
                    vv = float(raw)
                    if v_lo <= vv <= v_hi:
                        out.append((vv, ""))
                else:
                    # 粘连复原：扫描数字后缀子串
                    for i in range(len(raw)):
                        if not raw[i].isdigit():
                            continue
                        sub = raw[i:]
                        if re.fullmatch(r'\d+\.\d{2}', sub):
                            vv = float(sub)
                            if vv >= 100.0 and v_lo <= vv <= v_hi:
                                out.append((vv, "粘连复原"))
            else:
                # 漏点复原：5~8位连续数字按末两位为小数
                digits = re.sub(r'\D', '', raw)
                if 5 <= len(digits) <= 8:
                    vv = int(digits[:-2]) + int(digits[-2:]) / 100.0
                    if v_lo <= vv <= v_hi:
                        out.append((vv, "漏点复原"))
            return out

        def patch_family(bx0, by0, bx1, by1):
            # 候选文字patch在原图上的主色系；彩色像素不足→None（灰刻度/白tooltip字）
            bx0, by0 = max(0, int(bx0)), max(0, int(by0))
            bx1 = min(strip.shape[1], int(bx1) + 1)
            by1 = min(strip.shape[0], int(by1) + 1)
            if bx1 - bx0 < 3 or by1 - by0 < 3:
                return None
            hsv_p = cv2.cvtColor(strip[by0:by1, bx0:bx1], cv2.COLOR_BGR2HSV)
            sat = hsv_p[:, :, 1] > 80
            if int(sat.sum()) < 5:
                return None
            hue = float(np.median(hsv_p[:, :, 0][sat]))
            for cname, cfam in COLOR_FAMILY_T.items():
                if any(lo[0] <= hue <= hi[0]
                       for lo, hi in HSV_CURVE_COLORS.get(cname, [])):
                    return cfam
            return None

        # 颜色隔离：目标色→黑，其余→白
        b = strip[:, :, 0].astype(np.int16)
        g = strip[:, :, 1].astype(np.int16)
        r = strip[:, :, 2].astype(np.int16)
        if fam == "blue":
            m = (b - np.maximum(r, g) > 30) & (b > 100)
        elif fam == "warm":
            m = (r - g > 30) & (r - b > 50) & (r > 150)
        elif fam == "green":
            m = (g - np.maximum(r, b) > 30) & (g > 100)
        else:
            hsv_s = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
            m = (hsv_s[:, :, 1] > 80) & (hsv_s[:, :, 2] > 100)
        iso = np.full(strip.shape[:2], 255, np.uint8)
        iso[m] = 0

        SCALE = 4
        iso_up = cv2.GaussianBlur(cv2.resize(iso, None, fx=SCALE, fy=SCALE,
                                             interpolation=cv2.INTER_CUBIC), (3, 3), 0)
        variants = [(cv2.cvtColor(iso_up, cv2.COLOR_GRAY2BGR), "iso"),
                    (cv2.resize(strip, None, fx=SCALE, fy=SCALE,
                                interpolation=cv2.INTER_CUBIC), "color")]

        cands = []  # [(v, tag, raw)]，均已通过原图同色系patch校验
        for var, src in variants:
            try:
                lines = self._run_ocr(var)
            except Exception as e:
                print(f"[DEBUG] 定点OCR调用失败({curve.name},{src}): {e}")
                continue
            for box, (txt, _score) in lines:
                vals = parse_vals(txt)
                if not vals:
                    continue
                xs_bb = [p[0] for p in box]
                ys_bb = [p[1] for p in box]
                pf = patch_family(min(xs_bb) / SCALE, min(ys_bb) / SCALE,
                                  max(xs_bb) / SCALE, max(ys_bb) / SCALE)
                if pf != fam:
                    continue
                for vv, tag in vals:
                    cands.append((vv, tag, txt))
        if not cands:
            print(f"[DEBUG] 定点OCR: {curve.name} 峰值区未识别到同色系数值，跳过")
            return None

        # 同值去重后取与gmax最接近者；差>=12%拒绝（OCR误读防护）
        uniq = {}
        for vv, tag, txt in cands:
            uniq.setdefault(round(vv, 2), (vv, tag, txt))
        vv, tag, txt = min(uniq.values(),
                           key=lambda c: abs(c[0] - gmax) / max(abs(gmax), 1e-6))
        d = abs(vv - gmax) / max(abs(gmax), 1e-6)
        if d >= 0.12:
            # V4.9：拒绝前先做数字级纠错——标注误读（26960.82->20960.81）
            # 与曲线像素峰值必然差十几个百分点以上，而形近替换一位即可
            # 吻合；以P98稳健峰值为独立量测（圆点假锚不得作证），
            # 函数内8%/3%门控保证不误纠正确值
            _ys98 = np.array([p[1] for p in curve.points], dtype=float)
            _p98 = float(np.percentile(_ys98, 98)) if len(_ys98) else gmax
            rep = self._repair_ocr_number(vv, _p98)
            if rep is not None:
                rv, rerr = rep
                print(f"[FIX] 定点OCR数字纠错: {curve.name} {vv:.2f} -> {rv:.2f} "
                      f"(曲线峰值{gmax:.2f}佐证，误差{rerr:.1%})")
                vv, d = rv, rerr
            else:
                print(f"[DEBUG] 定点OCR: {curve.name} 候选 {vv:.2f} 与曲线峰值 {gmax:.2f} "
                      f"差{d:.1%}>=12%，拒绝")
                return None
        print(f"[INFO] 定点OCR: {curve.name} 峰值区识别 '{txt}' -> {vv:.2f} "
              f"(与曲线峰值差{d:.1%})")
        return {"text": txt, "v": vv, "t": t_pk, "fam": fam, "tag": f"定点OCR{tag}"}

    def _snap_price_annotations(self, img: np.ndarray, panel: Dict,
                                axis: AxisInfo, curves: List[CurveData]):
        """
        峰值标注吸附 V3.6（颜色优先混合+定点二次OCR版，适用于所有折线面板）：
        图上峰值标注文字印着该曲线当日精确最大值。
        1) 候选收集三通道：
           a. 正常通道：原文带小数点且值在扩展值域内；
           b. 粘连复原：带小数点但超值域（多与Y轴刻度粘连，如'815618.55'），
              扫描数字后缀子串，落在值域内且>=100的收为候选；
           c. 漏点复原：无小数点但含5~8位连续数字（橙字压在橙色曲线上时
              小数点常被OCR吞掉，如'6871784'），按末两位为小数复原；
           全部再经 位置±30px + 深色背景(tooltip白字)过滤 + 彩色像素检查；
        1.5) 定点二次OCR（V3.6）：对无候选覆盖的曲线（全图OCR漏读/熔读其标注），
           按峰值像素裁剪横条定向识别，候选与来源曲线直接绑定
           （详见 _targeted_peak_ocr，含同色系校验+12%门控）；
        2) 两阶段1:1贪心分配：
           第一阶段 同色系匹配 + 差<60%（颜色是强证据，容忍曲线被污染抬高）；
           第二阶段 纯数值就近 + 差<30%；标注与曲线各用一次；
           未映射的杂讯曲线（如填充渐变色产生的 green_曲线）不参与分配；
        3) 吸附：标注时间窗(±2.5h)内最高点设为标注值 + min(yy,v)全天封顶；
        4) 未分配标注打印DEBUG原因。
        该Dashboard的数值标注均为当日最大值标签。
        """
        # 坐标轴fallback的面板（被tooltip遮挡）不做吸附：
        # 否则tooltip数值会被当成峰值标注吸附到垃圾曲线上
        if getattr(axis, "used_fallback", False):
            return
        x, y, w, h = panel["rect"]
        texts = getattr(self, "text_data_all", [])
        inner = [t for t in texts
                 if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h]
        x0p, x1p = axis.x_pixel_range
        y0p, y1p = axis.y_pixel_range
        span_v = axis.y_max - axis.y_min
        v_lo = axis.y_min - 0.1 * span_v
        v_hi = axis.y_max + 0.2 * span_v

        COLOR_FAMILY = {"red": "warm", "orange": "warm", "yellow": "warm",
                        "green": "green", "cyan": "green",
                        "blue": "blue", "purple": "blue"}

        def hue_to_family(hue):
            for cname, fam in COLOR_FAMILY.items():
                if any(lo[0] <= hue <= hi[0]
                       for lo, hi in HSV_CURVE_COLORS.get(cname, [])):
                    return fam
            return None

        # ---- 1. 收集标注候选（三通道） ----
        anns = []
        for t in inner:
            cx, cy = t["center_x"], t["center_y"]
            if not (min(x0p, x1p) - 30 <= cx <= max(x0p, x1p) + 30):
                continue
            if not (min(y0p, y1p) - 30 <= cy <= max(y0p, y1p) + 30):
                continue
            raw = t["text"]
            # tooltip行形如'系列名：值'必含冒号；印刷峰值标注是纯数字，不含冒号
            if '：' in raw or ':' in raw:
                continue
            cands = []  # [(值, 复原标签)]
            if re.search(r'[.．]', raw):
                v = t.get("numeric_value")
                if v is not None and v_lo <= v <= v_hi:
                    cands.append((float(v), ""))
                elif v is not None:
                    # 粘连复原：如'815618.55'->'15618.55'、'14,020173.47'扫描后缀
                    s = raw.replace(',', '').replace('，', '')
                    for i in range(len(s)):
                        if not s[i].isdigit():
                            continue
                        sub = s[i:]
                        if re.fullmatch(r'\d+\.\d{2}', sub):
                            vv = float(sub)
                            if vv >= 100.0 and v_lo <= vv <= v_hi:
                                cands.append((vv, "粘连复原"))
                    if not cands:
                        print(f"[DEBUG] 标注 '{raw}'(v={v}) 超出扩展值域且后缀不可复原，跳过")
                        continue
                else:
                    continue
            else:
                # 漏点复原：橙字压橙色曲线时小数点常被吞（'6871784'->68717.84）
                digits = re.sub(r'\D', '', raw)
                if 5 <= len(digits) <= 8:
                    vv = int(digits[:-2]) + int(digits[-2:]) / 100.0
                    if v_lo <= vv <= v_hi:
                        cands.append((vv, "漏点复原"))
                if not cands:
                    continue

            xs_bb = [p[0] for p in t["bbox"]]
            ys_bb = [p[1] for p in t["bbox"]]
            bx0, bx1 = int(min(xs_bb)), int(max(xs_bb))
            by0, by1 = int(min(ys_bb)), int(max(ys_bb))
            patch = img[max(0, by0):by1 + 1, max(0, bx0):bx1 + 1]
            if patch.size == 0:
                continue
            hsv_p = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            # 深色背景过滤：tooltip白字浮层不是峰值标注
            if float(np.mean(hsv_p[:, :, 2])) < 120:
                print(f"[DEBUG] 标注 '{raw}' 位于深色背景(tooltip?)，跳过")
                continue
            # 峰值标注为彩色文字；白色tooltip字/黑色刻度字没有足够彩色像素
            sat = hsv_p[:, :, 1] > 80
            if int(sat.sum()) < 5:
                continue
            fam = hue_to_family(float(np.median(hsv_p[:, :, 0][sat])))
            # 文本左缘估算标注所指时刻
            t_ann = axis.x_min + (bx0 - 5 - x0p) / (x1p - x0p) * (axis.x_max - axis.x_min)
            for vv, tag in cands:
                anns.append({"text": raw, "v": vv, "t": t_ann, "fam": fam,
                             "tag": tag, "bbox": (bx0, by0, bx1, by1)})
                if tag:
                    print(f"[INFO] 标注{tag}: '{raw}' -> {vv:.2f}")

        # OCR偶发重复/复原多解：同值(±0.1%)同位(±0.5h)去重
        anns.sort(key=lambda a: (round(a["v"], 2), a["t"]))
        dedup = []
        for a in anns:
            if dedup and abs(a["v"] - dedup[-1]["v"]) <= max(abs(a["v"]) * 1e-3, 1e-6) \
                    and abs(a["t"] - dedup[-1]["t"]) < 0.5:
                continue
            dedup.append(a)
        anns = dedup

        # 未映射的杂讯曲线（如填充渐变色产生的 green_曲线）不参与标注分配
        valid_curves = [c for c in curves
                        if c.is_valid and c.points and '曲线' not in c.name]
        if not valid_curves:
            return

        # ---- 1.4 峰值圆点锚定（V3.7） ----
        # 先定位每条曲线的同色空心圆点：其Y像素反算值作为OCR候选选择锚点，
        # X像素反算时间作为峰值吸附时刻。避免“文字左缘时间”和“误读值就近匹配”
        # 两类系统性偏差。
        for c in valid_curves:
            marker = None
            # 全局“最高圆点”只用于出力面板；电价面板的峰值文字常与曲线重叠，
            # 文字中的0/6/8/9假圆会把锚点抬到错误高度（如538.50被抬到675）。
            if panel.get("subtype", "").startswith("load_"):
                marker = self._find_curve_peak_marker(img, panel, axis, c)
            if marker:
                c._peak_marker_value = marker["value"]
                c._peak_marker_time = marker["time"]
                c._peak_marker_px = (marker["cx"], marker["cy"])
            else:
                c._peak_marker_value = None
                c._peak_marker_time = None
                c._peak_marker_px = None

        # ---- 1.5 定点二次OCR（V3.6/V3.7）：全图OCR漏读/熔读的峰值标注定向识别 ----
        # 对没有候选覆盖（全图OCR未读到其标注）的曲线，在峰值像素位置裁剪横条识别。
        # V3.7：覆盖判定阈值2%→0.3%。若候选与圆点锚点差0.3%~2%，仍启动定点OCR复核，
        # 防止“68717.84误读为68141.84但离曲线峰值更近”时错误跳过。
        for ci, c in enumerate(valid_curves):
            ys_c = np.array([p[1] for p in c.points], dtype=float)
            # V4.3：P98稳健峰值。平台型曲线（非市场化预测13941）的全局max
            # 易被圆环/同色标注文字污染（20780.50），导致定点OCR候选被
            # 12%阈值误拒；P98对单点污染免疫，且对正常尖峰曲线仅略低。
            gmax_c = float(np.percentile(ys_c, 98)) if len(ys_c) else 0.0
            marker_v = getattr(c, "_peak_marker_value", None)
            # 圆点锚点与P98偏差>25%时判定为文字假圆/污染，弃用
            if marker_v is not None and gmax_c > 0 and \
                    abs(marker_v - gmax_c) / max(abs(gmax_c), 1e-6) > 0.25:
                print(f"[DEBUG] 圆点锚点{marker_v:.2f}与P98稳健峰值"
                      f"{gmax_c:.2f}偏差>25%，判定污染弃用: {c.name}")
                marker_v = None
                c._peak_marker_time = None   # 值是污染的，时间同样不可信
                c._peak_marker_value = None  # 同步清除，避免后续分配阶段误用
            anchor_v = marker_v or gmax_c
            anchor_t = getattr(c, "_peak_marker_time", None)
            if anchor_t is None:
                imax = max(range(len(c.points)), key=lambda i: c.points[i][1])
                anchor_t = c.points[imax][0]
            if any(abs(a["v"] - anchor_v) <= max(abs(anchor_v) * 0.003, 1e-6)
                   for a in anns):
                continue  # 已有候选精确覆盖该曲线
            res = self._targeted_peak_ocr(img, panel, axis, c, anchor_v,
                                          anchor_t,
                                          COLOR_FAMILY.get(c.color_name),
                                          v_lo, v_hi)
            if res:
                res["curve_ci"] = ci
                anns.append(res)
        if not anns:
            return

        # ---- 2. 两阶段1:1贪心分配 ----
        # 第一阶段：同色系（颜色是强证据，阈值放宽到60%，容忍曲线被污染抬高）。
        # V3.8：多色面板禁用“无颜色标注跨曲线就近分配”，防止蓝色68316.00
        # 被分配到橙色全网实时曲线。纯数值兜底仅允许单曲线面板使用。
        assigned = {}
        used = set()
        stages = [("颜色系", True, 0.60)]
        if len(valid_curves) <= 1:
            stages.append(("数值", False, 0.30))
        for stage_name, use_color, thr in stages:
            ps = []
            for ai, a in enumerate(anns):
                if ai in assigned:
                    continue
                if "curve_ci" in a:
                    continue  # 定点OCR候选走第三遍直接绑定
                for ci, c in enumerate(valid_curves):
                    if ci in used:
                        continue
                    if use_color:
                        if a["fam"] is None or COLOR_FAMILY.get(c.color_name) != a["fam"]:
                            continue
                    gmax = max(p[1] for p in c.points)
                    anchor_v = getattr(c, "_peak_marker_value", None) or gmax
                    d = abs(anchor_v - a["v"]) / max(abs(a["v"]), 1e-6)
                    if d < thr:
                        ps.append((d, ai, ci))
            ps.sort(key=lambda p: p[0])
            for d, ai, ci in ps:
                if ai in assigned or ci in used:
                    continue
                assigned[ai] = (ci, d, stage_name)
                used.add(ci)

        # 第三遍：定点OCR候选与来源曲线绑定；V3.8再次校验颜色，杜绝跨色写入
        for ai, a in enumerate(anns):
            ci = a.get("curve_ci")
            if ci is None or ai in assigned or ci in used:
                continue
            curve0 = valid_curves[ci]
            if a.get("fam") and COLOR_FAMILY.get(curve0.color_name) != a["fam"]:
                print(f"[WARN] 定点OCR候选跨色拒绝: {a['text']} -> {curve0.name}")
                continue
            gmax_c = max(p[1] for p in curve0.points)
            anchor_c = getattr(curve0, "_peak_marker_value", None) or gmax_c
            d_c = abs(anchor_c - a["v"]) / max(abs(a["v"]), 1e-6)
            assigned[ai] = (ci, d_c, "定点OCR")
            used.add(ci)

        # ---- 3. 吸附 + 封顶 ----
        for ai, a in enumerate(anns):
            if ai not in assigned:
                print(f"[DEBUG] 标注 '{a['text']}'(v={a['v']:.2f}) 无匹配曲线，跳过")
                continue
            ci, d, stage_name = assigned[ai]
            curve = valid_curves[ci]
            v = a["v"]

            # V4.9：吸附前数字级纠错。颜色分配门控宽至60%，误读标注
            # （26960.82->20960.81，差27%）也会被分配并封顶成错误平台；
            # 以P98稳健峰值为独立量测还原印刷真值（圆点假锚18234不得
            # 作证——太阳能15066.57曾被误纠成18066.57）。函数内8%门控
            # 保证正确识别（如26960.82、15066.57）不被触碰。
            _anchor_rep = None
            if curve.points:
                _ys = np.array([p[1] for p in curve.points], dtype=float)
                _anchor_rep = float(np.percentile(_ys, 98)) if len(_ys) else None
            if _anchor_rep and abs(_anchor_rep) > 1e-6:
                _rep = self._repair_ocr_number(v, _anchor_rep)
                if _rep is not None:
                    _rv, _rerr = _rep
                    _dev = abs(v - _anchor_rep) / abs(_anchor_rep)
                    print(f"[FIX] 峰值标注数字纠错: {curve.name} {v:.2f} -> "
                          f"{_rv:.2f} (P98稳健峰值{_anchor_rep:.2f}佐证，"
                          f"误差{_rerr:.1%}，原偏差{_dev:.1%})")
                    v = _rv
                    a["v"] = _rv

            # V3.8：印刷峰值标注是强证据，不再被像素锚点否决。
            # 全局圆点可能误检平台线/文字圆环（如13941.00首点），仅用于排序；
            # 此处必须保证OCR峰值进入CSV。
            anchor_v = getattr(curve, "_peak_marker_value", None)
            if anchor_v is not None and abs(v - anchor_v) / max(abs(v), 1e-6) > 0.60:
                print(f"[WARN] 峰值标注与圆点锚点差>60%，仍按OCR峰值写入: "
                      f"{curve.name} {v:.2f} vs {anchor_v:.2f}")

            xs96 = [p[0] for p in curve.points]
            ys96 = [p[1] for p in curve.points]
            ann_marker = self._find_annotation_marker(img, panel, axis, curve, a)
            marker_t = (ann_marker or {}).get("time",
                                               getattr(curve, "_peak_marker_time", None))
            if marker_t is not None:
                # 圆点中心直接对应真实数据点，吸附到最近的96点网格
                imax = min(range(len(xs96)), key=lambda i: abs(xs96[i] - marker_t))
                time_src = "标注圆点中心" if ann_marker else "曲线峰值圆点"
                # V4.3：圆心检测存在±3px系统偏差（≈1个15分钟时点，如太阳能
                # 15618.55被定到09:00而非09:15）。峰值标注标记的是“曲线最
                # 高点”，允许以曲线实际最高点复核，但必须同时满足：
                #   1) 偏移<=0.3h（一个15分钟时点）——防止68316被提取噪声
                #      从11:15拉到10:15、12173.47从00:15拉到00:30；
                #   2) 值增益>=1%——平台型曲线（非市场化13941）平坦区0.5%
                #      噪声增益不足以搬移，尖峰曲线（太阳能2.3%）才复核；
                #   3) 边缘时点（<0.4h，如00:15首点）圆点可靠，不再复核。
                if marker_t >= 0.4:
                    win = [i for i, xx in enumerate(xs96)
                           if abs(xx - marker_t) <= 0.6]
                    if len(win) >= 2:
                        i_local = max(win, key=lambda i: ys96[i])
                        gain = (ys96[i_local] - ys96[imax]) / max(abs(v), 1e-6)
                        if (i_local != imax and
                                abs(xs96[i_local] - marker_t) <= 0.3 and
                                gain >= 0.01):
                            print(f"[DEBUG] 峰值时点复核: {curve.name} 圆点"
                                  f"{xs96[imax]:.2f}h -> 曲线最高点"
                                  f"{xs96[i_local]:.2f}h (增益{gain:.1%})")
                            imax = i_local
                            time_src += "+曲线最高点复核"
            else:
                # 兜底：保留旧逻辑（标注文字左缘±2.5h内取曲线最高点）
                win = [i for i, xx in enumerate(xs96) if abs(xx - a["t"]) <= 2.5]
                if win:
                    imax = max(win, key=lambda i: ys96[i])
                else:
                    imax = max(range(len(ys96)), key=lambda i: ys96[i])
                time_src = "文字左缘兜底"

            # 吸附峰值 + 全天封顶（标注即当日最大值，曲线超过说明被污染）
            curve.points = [(xx, min(yy, v)) if i != imax else (xx, v)
                            for i, (xx, yy) in enumerate(curve.points)]
            # V4.3：被封到与峰值同值的其它点降0.01，保证全天最大值时点唯一
            # （否则max@时点会漂移到并列的第一个点，如15618.55报在09:00）
            curve.points = [(xx, (yy - 0.01 if (i != imax and yy >= v) else yy))
                            for i, (xx, yy) in enumerate(curve.points)]
            # V4.2 canonical peak guard：供所有CSV导出后回读校验/强制落盘
            curve._peak_snapped_value = float(v)
            curve._peak_snapped_time = float(xs96[imax])
            curve._peak_guard_cap = True  # 印刷峰值是全天峰值，其他点不得超过
            print(f"[INFO] 峰值吸附: {curve.name} -> {v:.2f} @ {xs96[imax]:.2f}h "
                  f"({time_src}, 标注'{a['text']}'{a['tag']}, {stage_name}匹配, 差{d:.1%})")

    def _merged_contributors(self) -> Dict[str, object]:
        """V4.8：合并总表各列的数据来源面板（与_export_merged_csv
        同序同条件：主日期、未拒绝、非fallback、首插优先）。
        峰值守卫写入合并表时按此过滤——别日面板的标注不得落到当日列
        （05-17电量标注13468.38曾压盖05-02列的14028.61峰值）。"""
        from collections import Counter
        dates = [getattr(r, "panel_date", "unknown") for r in self.panel_results]
        dates = [d for d in dates if d != "unknown"]
        target = Counter(dates).most_common(1)[0][0] if dates else None
        contrib = {}
        for res in self.panel_results:
            if target and getattr(res, "panel_date", "unknown") != target:
                continue
            if getattr(res, "is_valid", True) is False:
                continue
            if getattr(res.axis_info, "used_fallback", False):
                continue
            col_map = MERGE_COLUMN_MAP.get(getattr(res, "panel_subtype", ""), {})
            for curve in res.curves:
                if not curve.is_valid or not curve.points:
                    continue
                col = col_map.get(curve.name)
                if not col or col in contrib:
                    continue
                if len(curve.points) < 90:
                    continue
                contrib[col] = res
        return contrib

    def _peak_guard_entries(self) -> List[Dict]:
        """收集所有已吸附峰值，作为CSV导出后的canonical校验依据。"""
        entries = []
        for res in self.panel_results:
            col_map = MERGE_COLUMN_MAP.get(
                getattr(res, "panel_subtype", ""), {})
            for curve in res.curves:
                v = getattr(curve, "_peak_snapped_value", None)
                t = getattr(curve, "_peak_snapped_time", None)
                if v is None or t is None:
                    continue
                entries.append({
                    "result": res,
                    "curve": curve,
                    "panel_col": curve.name,
                    "merged_col": col_map.get(curve.name, curve.name),
                    "value": float(v),
                    "time": float(t),
                    "cap": bool(getattr(curve, "_peak_guard_cap", False)),
                })
        return entries

    def _apply_peak_guards_to_df(self, df: pd.DataFrame, entries: List[Dict],
                                 col_key: str, context: str) -> bool:
        """把canonical峰值强制写入DataFrame，返回是否发生修改。"""
        if "时间" not in df.columns:
            return False
        changed = False
        for e in entries:
            col = e[col_key]
            if col not in df.columns:
                continue
            # 00:15是第1行，11:15是第45行；直接按时点定位，避免时间字符串差异
            idx = int(round(e["time"] * 4)) - 1
            idx = max(0, min(len(df) - 1, idx))
            series = pd.to_numeric(df[col], errors="coerce")
            if e["cap"]:
                capped = series.clip(upper=e["value"])
                if not capped.equals(series):
                    df[col] = capped
                    series = capped
                    changed = True
            current = pd.to_numeric(pd.Series([df.loc[idx, col]]), errors="coerce").iloc[0]
            if pd.isna(current) or abs(float(current) - e["value"]) > 1e-6:
                df.loc[idx, col] = e["value"]
                changed = True
                print(f"[FIX] {context}: {col} -> {e['value']:.2f} @ "
                      f"{e['time']:.2f}h")
        return changed

    def _refresh_panel_csvs(self):
        """所有校正完成后，二次重写每个面板CSV，确保与最终内存曲线一致。"""
        for res in self.panel_results:
            if not getattr(res, "output_csv", None):
                continue
            self.export_to_csv(res, res.output_csv)
            entries = [e for e in self._peak_guard_entries()
                       if e["result"] is res]
            try:
                df = pd.read_csv(res.output_csv, encoding="utf-8-sig")
                if self._apply_peak_guards_to_df(df, entries, "panel_col",
                                                 os.path.basename(res.output_csv)):
                    df.to_csv(res.output_csv, index=False, encoding="utf-8-sig")
            except Exception as exc:
                print(f"[WARN] 面板CSV峰值复核失败: {res.output_csv}: {exc}")
        print("[INFO] 全部面板CSV已按最终曲线二次落盘")

    def _verify_exports_consistency(self, output_dir: str, base_name: str):
        """回读面板CSV/合并CSV，确保吸附峰值没有只停留在日志里。"""
        entries = self._peak_guard_entries()
        if not entries:
            return
        for res in self.panel_results:
            path = getattr(res, "output_csv", None)
            if not path or not os.path.exists(path):
                continue
            sub = [e for e in entries if e["result"] is res]
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
                if self._apply_peak_guards_to_df(df, sub, "panel_col",
                                                 os.path.basename(path)):
                    df.to_csv(path, index=False, encoding="utf-8-sig")
            except Exception as exc:
                print(f"[WARN] 面板CSV回读校验失败: {path}: {exc}")

        merged_path = os.path.join(output_dir, f"{base_name}_merged_96points.csv")
        if os.path.exists(merged_path):
            try:
                # V4.8：合并表守卫必须来自该列的实际数据来源面板
                contrib = self._merged_contributors()
                m_entries = [e for e in entries
                             if contrib.get(e["merged_col"]) is e["result"]]
                df = pd.read_csv(merged_path, encoding="utf-8-sig")
                if self._apply_peak_guards_to_df(df, m_entries, "merged_col",
                                                 os.path.basename(merged_path)):
                    df.to_csv(merged_path, index=False, encoding="utf-8-sig")
            except Exception as exc:
                print(f"[WARN] 合并CSV回读校验失败: {merged_path}: {exc}")
        print(f"[CHECK] CSV导出一致性校验完成，峰值守卫{len(entries)}项")

    def _export_merged_csv(self, output_dir: str, base_name: str) -> Optional[str]:
        """
        跨面板合并总表：
        把各面板96点曲线按标准列名（电价/电量/负荷/各出力）合并成一张表。
        多日期面板自动取面板数量最多的日期。
        """
        from collections import Counter

        # 目标日期：面板数最多的日期（排除unknown）
        dates = [getattr(r, "panel_date", "unknown") for r in self.panel_results]
        dates = [d for d in dates if d != "unknown"]
        target = Counter(dates).most_common(1)[0][0] if dates else None

        merged: Dict[str, list] = {}
        time_labels = None

        for res in self.panel_results:
            subtype = getattr(res, "panel_subtype", "")
            date = getattr(res, "panel_date", "unknown")
            if target and date != target:
                continue  # 只取目标日期的面板
            # V4.3：被拒绝的面板（如负荷曲线退化拒导出）不并入总表
            if getattr(res, "is_valid", True) is False:
                print(f"[INFO] 合并表剔除被拒绝面板: {subtype}_{date}")
                continue
            if getattr(res.axis_info, "used_fallback", False):
                # 坐标轴标定失败的面板（如被tooltip遮挡），数据无意义，不并入总表
                print(f"[INFO] 合并表剔除fallback面板: {subtype}_{date}")
                continue
            col_map = MERGE_COLUMN_MAP.get(subtype, {})
            for curve in res.curves:
                if not curve.is_valid or not curve.points:
                    continue
                col = col_map.get(curve.name)
                if not col or col in merged:
                    continue
                xs = [p[0] for p in curve.points]
                ys = [round(p[1], 2) for p in curve.points]
                if len(ys) < 90:
                    continue
                if len(ys) > 96:
                    ys = ys[:96]
                merged[col] = ys
                if time_labels is None:
                    def _fmt_time(xv):
                        hh = int(xv)
                        mm = int(round((xv % 1) * 60))
                        if hh >= 24 or (hh == 23 and mm >= 60):
                            return "24:00"
                        return f"{hh:02d}:{mm:02d}"
                    time_labels = [_fmt_time(x) for x in xs]

        if not merged:
            print("[WARN] 无有效面板数据，未生成合并总表")
            return None

        # 固定输出标准96点：缺列也保留空列，避免下游因列缺失静默错位
        n = 96
        if not time_labels or len(time_labels) < n:
            time_labels = []
            for i in range(1, n + 1):
                total_min = i * 15
                hh, mm = total_min // 60, total_min % 60
                time_labels.append("24:00" if hh == 24 else f"{hh:02d}:{mm:02d}")

        df = pd.DataFrame({"时点": range(1, n + 1), "时间": time_labels[:n]})
        for col in MERGE_COLUMN_ORDER:
            vals = merged.get(col)
            if vals is None:
                df[col] = [np.nan] * n
            else:
                df[col] = (vals + [np.nan] * n)[:n]

        missing = [c for c in MERGE_COLUMN_ORDER if df[c].notna().sum() == 0]
        if missing:
            print(f"[WARN] 合并总表仍有整列缺失: {missing}")

        path = os.path.join(output_dir, f"{base_name}_merged_96points.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"\n[INFO] 合并总表已保存: {path}")
        print(f"[INFO] 目标日期: {target} | 行数: {len(df)} | 列数: {len(df.columns)}")
        print("[INFO] 合并表预览（前5行）:")
        print(df.head().to_string(index=False))

        # 关键极值复核表：用于快速发现“值对但时点错/列错位”
        print("\n[CHECK] 合并表关键极值复核:")
        for col in MERGE_COLUMN_ORDER:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s) == 0:
                continue
            imax, imin = s.idxmax(), s.idxmin()
            print(f"  {col}: max={s.max():.2f}@{df.loc[imax, '时间']} | "
                  f"min={s.min():.2f}@{df.loc[imin, '时间']}")
        return path

    def _export_load_summary(self, output_dir: str, base_name: str) -> Optional[Dict]:
        """导出一张负荷汇总CSV和一张负荷汇总PNG（含tooltip锚点复核）。"""
        load_res = next((r for r in self.panel_results
                         if getattr(r, "panel_subtype", "") == "load"), None)
        if load_res is None or not load_res.curves:
            return None
        if load_res.axis_info is not None and self._load_curves_degenerate(
                load_res.curves, load_res.axis_info):
            print("[ERROR] 负荷曲线仍为直线/退化，拒绝导出错误的负荷汇总CSV")
            return None

        order = ["预测直调负荷", "预测全网负荷", "实际直调负荷", "实际全网负荷"]
        by_name = {c.name: c for c in load_res.curves}
        if not any(name in by_name for name in order):
            return None

        first = next(c for c in load_res.curves if c.points)
        xs = [p[0] for p in first.points]
        def _fmt(xv):
            total_min = int(round(xv * 60))
            hh, mm = total_min // 60, total_min % 60
            return "24:00" if hh == 24 else f"{hh:02d}:{mm:02d}"

        df = pd.DataFrame({"时点": range(1, len(xs) + 1),
                           "时间": [_fmt(v) for v in xs]})
        for name in order:
            c = by_name.get(name)
            df[name] = [round(p[1], 2) for p in c.points] if c is not None else np.nan

        csv_path = os.path.join(output_dir, f"{base_name}_load_summary.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        anchor = getattr(load_res, "_load_anchor", None)
        if not anchor:
            anchor = self._extract_load_tooltip_anchors(
                getattr(self, "text_data_all", []), load_res.chart_roi)
        t_anchor = anchor.get("time")
        anchor_values = anchor.get("values", {})

        font_prop = _cn_font_prop()
        plt.figure(figsize=(14, 7.5))
        styles = {
            "预测直调负荷": ("#18b7a5", "--", "预测直调负荷"),
            "实际直调负荷": ("#18b7a5", "-", "实际直调负荷"),
            "预测全网负荷": ("#f29f05", "--", "预测全网负荷"),
            "实际全网负荷": ("#f29f05", "-", "实际全网负荷"),
        }
        for name in order:
            c = by_name.get(name)
            if c is None:
                continue
            color, ls, label = styles[name]
            plt.plot([p[0] for p in c.points], [p[1] for p in c.points],
                     color=color, linestyle=ls, linewidth=2.0, label=label)

        if t_anchor is not None:
            plt.axvline(t_anchor, color="#4c78a8", linewidth=1.2, alpha=0.75)
            for name, value in anchor_values.items():
                if name in styles:
                    plt.scatter([t_anchor], [value], s=52,
                                color=styles[name][0], edgecolor="white", zorder=5)
            anchor_txt = "\n".join([f"{k}: {v:,.2f}" for k, v in anchor_values.items()])
            plt.annotate(f"tooltip锚点 {int(t_anchor):02d}:{int(round((t_anchor%1)*60)):02d}\n{anchor_txt}",
                         xy=(t_anchor, max(anchor_values.values(), default=0)),
                         xytext=(t_anchor + 0.7, max(anchor_values.values(), default=0) * 0.98),
                         fontsize=9, fontproperties=font_prop,
                         arrowprops=dict(arrowstyle="->", color="#4c78a8"),
                         bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#4c78a8", alpha=0.92))

        plt.title(f"山东电力负荷曲线汇总复核（{load_res.panel_date}）",
                  fontproperties=font_prop, fontsize=15)
        plt.xlabel("时间（小时）", fontproperties=font_prop)
        plt.ylabel("负荷（MW）", fontproperties=font_prop)
        ticks = np.arange(0, 24.01, 2)
        plt.xticks(ticks, [f"{int(h):02d}:00" for h in ticks])
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.18),
                   prop=font_prop)
        plt.tight_layout()
        png_path = os.path.join(output_dir, f"{base_name}_load_summary.png")
        plt.savefig(png_path, dpi=180, bbox_inches="tight")
        plt.close()

        print(f"[INFO] 负荷汇总CSV: {csv_path}")
        print(f"[INFO] 负荷汇总PNG: {png_path}")
        return {"csv": csv_path, "png": png_path}

    def _process_panel(self, img: np.ndarray, panel: Dict,
                       output_dir: str, base_name: str) -> ExtractionResult:
        """处理单个面板：坐标标定 → 曲线提取 → 插值 → 导出"""
        rect = panel["rect"]
        x, y, w, h = rect
        print(f"\n---- 处理面板 [{panel['slug']}] ----")

        result = ExtractionResult(image_path=self._current_image, chart_roi=rect)
        result.panel_subtype = panel.get("subtype", "")
        result.panel_date = panel.get("date", "unknown")

        # 坐标标定（复用全图OCR结果，注意必须用 text_data_all，
        # self.text_data 会被 extract_axis_info 覆盖为面板子集）
        texts_all = getattr(self, "text_data_all", self.text_data)
        axis = self.extract_axis_info(img, rect, texts=texts_all)
        result.axis_info = axis
        result.text_data = [t for t in texts_all
                            if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h]

        # 曲线提取
        # 太阳能面板：夜间无数据段填0（光伏夜间不发电）
        # 注意：标志必须保持到插值完成后才能复位（插值在下方执行）
        subtype = panel.get("subtype", "")
        self._zero_fill_gap = "太阳能" in subtype
        # 电价面板：禁用平滑，保留阶梯形态
        self._no_smooth = subtype == "price"

        if subtype == "load":
            # 负荷面板预测/实际为同色系，需按实线/虚线分离，不能按颜色命名。
            # 裁剪图中图例可能位于绘图区内部，必须先剔除，否则图例色块会被当曲线。
            if not panel.get("legend_boxes"):
                panel["legend_boxes"] = [
                    t["bbox"] for t in texts_all
                    if x <= t["center_x"] <= x + w and y <= t["center_y"] <= y + h
                    and ("直调负荷" in t["text"] or "全网负荷" in t["text"])
                    and ":" not in t["text"] and "：" not in t["text"]
                ]

            # V3.9：负荷面板优先用像素几何重建坐标轴。
            # tooltip遮挡Y轴时，OCR轴标定可能退化（真实案例中全列1989.28），
            # 蓝色X轴端点+顶部100000网格线比OCR刻度更可靠。
            visual_axis = self._detect_load_axis_visual(
                img, rect, panel.get("legend_boxes", []), axis)
            if visual_axis is not None:
                axis = visual_axis
                # V4.4：蓝线右端延出时，用hover竖线+tooltip时间修正X映射
                axis = self._refine_load_x_axis_by_hover(img, rect, axis, texts_all)
                result.axis_info = axis
                self._last_axis = axis  # V4.3：负荷面板换轴后同步刷新全局轴

            # V4.5：提前解析tooltip锚点，供虚线合成用“锚点差”填充重合时段
            early_anchor = self._extract_load_tooltip_anchors(texts_all, rect)
            curves = self._extract_load_style_curves(
                img, rect, axis, panel.get("legend_boxes", []),
                tooltip_anchor=early_anchor)
        else:
            curves = self.extract_curves(img, rect, axis)

        # V3.8：负荷四条曲线若退化为常数（如全列1989.28），
        # 说明轴标定或图例遮罩失败；用图例底部+网格线+X轴蓝线重建后再提取。
        if subtype == "load" and self._load_curves_degenerate(curves, axis):
            rescued_axis = self._rescue_load_axis_geometry(
                img, rect, axis, panel.get("legend_boxes", []))
            if rescued_axis is not None:
                axis = rescued_axis
                axis = self._refine_load_x_axis_by_hover(img, rect, axis, texts_all)
                result.axis_info = axis
                self._last_axis = axis  # V4.3：同步刷新全局轴
                curves = self._extract_load_style_curves(
                    img, rect, axis, panel.get("legend_boxes", []),
                    tooltip_anchor=early_anchor)

        # 按面板类型映射曲线名称（该Dashboard图例配色固定）
        if subtype in PANEL_CURVE_MAP:
            cmap = PANEL_CURVE_MAP[subtype]
        elif subtype.startswith("load_"):
            cmap = PANEL_CURVE_MAP["load_gen"]   # 出力面板（太阳能/风电/全网等）
        else:
            cmap = PANEL_CURVE_MAP.get(panel["type"], {})
        if subtype != "load":  # load专用分离已直接命名，不能再用颜色覆盖
            for c in curves:
                if c.color_name in cmap:
                    c.name = cmap[c.color_name]

        # 同名曲线去重：同一曲线被相邻色相（orange/yellow）拆成两条时，
        # 映射后会撞名，保留像素点多者（数据更完整）
        curves_sorted = sorted(curves, key=lambda c: len(c.pixel_points), reverse=True)
        deduped, name_seen = [], set()
        for c in curves_sorted:
            if c.name in name_seen:
                print(f"[INFO] 同名曲线去重: 丢弃 {c.name}"
                      f"({c.color_name}, {len(c.pixel_points)}点)")
                continue
            name_seen.add(c.name)
            deduped.append(c)
        curves = deduped

        # 插值到96点
        for curve in curves:
            if curve.is_valid:
                self.interpolate_to_96points(curve)

        # V3.9：插值后再次检查退化。某些原始曲线只来自图例/遮挡框，
        # 插值前看似有多个像素，插值后才会暴露为全列同一常数。
        if subtype == "load" and self._load_curves_degenerate(curves, axis):
            print("[WARN] 插值后负荷曲线退化，启动视觉轴重提")
            recovered_axis = (self._detect_load_axis_visual(
                img, rect, panel.get("legend_boxes", []), axis) or
                self._rescue_load_axis_geometry(
                    img, rect, axis, panel.get("legend_boxes", [])))
            if recovered_axis is not None:
                axis = recovered_axis
                axis = self._refine_load_x_axis_by_hover(img, rect, axis, texts_all)
                result.axis_info = axis
                self._last_axis = axis  # V4.3：同步刷新全局轴
                curves = self._extract_load_style_curves(
                    img, rect, axis, panel.get("legend_boxes", []),
                    tooltip_anchor=early_anchor)
                for curve in curves:
                    curve._axis = axis
                    if curve.is_valid:
                        self.interpolate_to_96points(curve)

        self._zero_fill_gap = False
        self._no_smooth = False

        # V3.8：负荷面板tooltip是最精确的11:15校验锚点，
        # 对四条曲线做整体微量比例校正并强制写入该时点。
        if subtype == "load":
            load_anchor = self._extract_load_tooltip_anchors(texts_all, rect)
            refined_time = self._refine_load_tooltip_time_by_ocr(img, rect)
            if refined_time is not None and (load_anchor.get("time") is None or
                                             abs(load_anchor.get("time", 0) % 1) < 1e-6):
                load_anchor["time"] = refined_time
            hover_time = self._detect_load_hover_time(img, rect, axis)
            # OCR只识别到“11:预测...”时先用11.0占位；蓝色竖线作最后兜底。
            if hover_time is not None and (load_anchor.get("time") is None or
                                           abs(load_anchor.get("time", 0) % 1) < 1e-6):
                load_anchor["time"] = hover_time
            # V5.0b：tooltip时间OCR误读防护——蓝色竖线是独立像素量测，
            # 与OCR时刻冲突>0.1h时采信竖线（05-03抬头"11:00"曾被误判
            # "11:15"，四条曲线锚点整体错写晚15分钟、峰值84065移位）。
            elif (hover_time is not None and load_anchor.get("time") is not None and
                    abs(load_anchor["time"] - hover_time) > 0.10):
                print(f"[WARN] 负荷tooltip时间OCR({load_anchor['time']:.2f}h)"
                      f"与蓝色竖线({hover_time:.2f}h)冲突，采信竖线"
                      f"（OCR误读防护）")
                load_anchor["time"] = hover_time
            self._snap_load_tooltip_anchors(curves, load_anchor)
            result._load_anchor = load_anchor

        # 所有折线面板：用图上峰值标注（如 715.93/68316.00）校正曲线峰值
        # 该Dashboard的标注即当日最大值，是最可靠的数据源
        if panel.get("type") != "info" and subtype != "load":
            # 负荷面板没有峰值印刷标注；tooltip数值带冒号且会遮挡，不能参与吸附
            self._snap_price_annotations(img, panel, axis, curves)

        # ==================== 山东电力市场规则钳制 ====================
        # 1. 出清电价（日前/实时）下限 -80 元/MWh（申报价区间[-80, 1500]）
        # 2. 出力/负荷/电量 物理量非负
        for curve in curves:
            if not curve.is_valid or not curve.points:
                continue
            if panel.get("subtype") == "price":
                curve.points = [(px, max(py, -80.0)) for px, py in curve.points]
            elif panel.get("type") in ("load", "clearing"):
                curve.points = [(px, max(py, 0.0)) for px, py in curve.points]

        # ==================== V4.3 负荷导出前最终守卫 ====================
        # 主提取退化→换轴重提→再退化时，启用与主路径完全独立的
        # 逐列直采兜底（第二数据源），仍失败则拒绝导出直线CSV。
        if subtype == "load" and self._load_curves_degenerate(curves, axis):
            print("[WARN] 导出前负荷曲线仍退化，启动独立视觉兜底提取")
            fb = self._extract_load_curves_visual_fallback(
                img, rect, axis, panel.get("legend_boxes", []),
                tooltip_anchor=early_anchor)
            if fb:
                for curve in fb:
                    if curve.is_valid:
                        self.interpolate_to_96points(curve)
                if getattr(result, "_load_anchor", None):
                    self._snap_load_tooltip_anchors(fb, result._load_anchor)
                for curve in fb:  # 物理量非负钳制
                    if curve.is_valid and curve.points:
                        curve.points = [(pxx, max(pyy, 0.0))
                                        for pxx, pyy in curve.points]
                if not self._load_curves_degenerate(fb, axis):
                    curves = fb
                    print("[INFO] 独立视觉兜底提取成功，采用兜底曲线")

        result.curves = curves

        # 验证
        result = self.validate_result(result)

        # V4.3：负荷曲线经主提取/恢复/兜底后仍退化——拒绝导出直线CSV，
        # 宁可缺文件也不让错误数据进入合并表；JSON/可视化仍保留便于排查
        load_csv_rejected = (subtype == "load" and
                             self._load_curves_degenerate(curves, axis))
        if load_csv_rejected:
            print("[ERROR] 负荷曲线仍为直线/退化，拒绝导出该面板96点CSV")
            result.is_valid = False
            result.error_msg = "负荷曲线退化，CSV导出被拒绝"

        # 导出
        if not load_csv_rejected:
            csv_path = os.path.join(output_dir, f"{base_name}_{panel['slug']}_96points.csv")
            self.export_to_csv(result, csv_path)
        json_path = os.path.join(output_dir, f"{base_name}_{panel['slug']}_metadata.json")
        self.export_to_json(result, json_path)
        viz_path = os.path.join(output_dir, f"{base_name}_{panel['slug']}_visualization.png")
        self.visualize(img, result, viz_path)

        return result

    # --------------------------------------------------------------------------
    # 主流程
    # --------------------------------------------------------------------------
    def process(self, image_input, output_dir: str = "./output", progress_callback=None) -> ExtractionResult:
        """
        完整处理流程（V2：先检测多面板，逐面板独立提取；无面板时回退单图模式）

        Args:
            image_path: 输入图片路径
            output_dir: 输出目录

        Returns:
            ExtractionResult: 提取结果（多面板模式返回第一个面板的结果，
                              全部结果在 self.panel_results）
        """
        import time
        start_time = time.time()

        os.makedirs(output_dir, exist_ok=True)
        base_name = "chart" if isinstance(image_input, bytes) else Path(image_input).stem
        self._current_image = base_name

        def _cb(pct, msg):
            if progress_callback:
                progress_callback(pct, msg)

        result = ExtractionResult(image_path=image_path)
        self.panel_results = []

        try:
            print(f"\n{'='*60}")
            print(f"[START] 处理图像: {image_path}")
            print(f"{'='*60}")

            # 1. 预处理
            _cb(5, "正在预处理图片...")
            img = self.preprocess_image(image_input)

            # 2. 全图OCR一次（所有面板复用，省时）
            _cb(15, "正在执行OCR...")
            ocr_all = self._run_ocr(img)
            self.text_data_all = self._build_text_entries(ocr_all, 0, 0)
            self.text_data = self.text_data_all  # 供调试落盘
            self._dump_ocr_debug(output_dir, base_name)

            # 3. 检测图表面板
            _cb(35, "正在检测面板...")
            panels = self.detect_panels(img, self.text_data_all)

            if panels:
                # ================= 多面板模式 =================
                print(f"[INFO] 进入多面板模式: {len(panels)} 个面板")
                # V4.8：只处理主日期面板——Dashboard截图常带相邻日期的
                # 历史小面板（如05-02截图里的05-17/05-18电量面板），
                # 不剔除会把别日数据和峰值标注混进当日总表（05-17的
                # 13468.38曾压盖05-02的14028.61峰值）。剔后既不生成
                # 别日面板文件，合并表/峰值守卫也只含当日数据。
                from collections import Counter
                _pdates = [p.get("date", "unknown") for p in panels
                           if p.get("type") != "info"]
                _pdates = [d for d in _pdates if d and d != "unknown"]
                if _pdates:
                    _target = Counter(_pdates).most_common(1)[0][0]
                    _keep = [p for p in panels
                             if p.get("type") == "info"
                             or p.get("date", "unknown") in ("unknown", _target)]
                    if len(_keep) < len(panels):
                        print(f"[INFO] 主日期={_target}，剔除非主日期面板 "
                              f"{len(panels) - len(_keep)} 个"
                              f"（不提取、不导出、不并入总表）")
                        panels = _keep
                for idx, panel in enumerate(panels):
                    if panel["type"] == "info":
                        print(f"[INFO] 跳过柱状图面板（暂不支持）: {panel['slug']}")
                        continue
                    try:
                        _cb(45 + min(idx * 8, 40), f"正在处理面板: {panel.get('slug', idx)}")
                        res = self._process_panel(img, panel, output_dir, base_name)
                        self.panel_results.append(res)
                    except Exception as pe:
                        print(f"[WARN] 面板 {panel['slug']} 处理失败: {pe}")
                result = self.panel_results[0] if self.panel_results else result

                # 跨面板合并总表（日前/实时电价 + 电量 + 负荷 + 各出力）
                if self.panel_results:
                    # V4.2：先按最终内存曲线二次重写全部面板CSV，
                    # 防止面板CSV停留在吸附前的直线/旧值版本。
                    self._refresh_panel_csvs()
                    self._export_merged_csv(output_dir, base_name)
                    # 负荷四条曲线单独汇总，便于直接核对tooltip和训练/预测模型
                    self._export_load_summary(output_dir, base_name)
                    # 最后回读CSV，把OCR峰值守卫强制落实到面板CSV和合并CSV
                    self._verify_exports_consistency(output_dir, base_name)
            else:
                # ================= 单图模式（旧流程） =================
                _cb(40, "未检测到面板，使用单图模式...")
                roi = self.detect_chart_roi(img)
                result.chart_roi = roi

                axis = self.extract_axis_info(img, roi,
                                              texts=getattr(self, "text_data_all", self.text_data))
                result.axis_info = axis
                result.text_data = getattr(self, 'text_data', [])

                curves = self.extract_curves(img, roi, axis)
                for curve in curves:
                    if curve.is_valid:
                        self.interpolate_to_96points(curve)
                result.curves = curves
                result = self.validate_result(result)

                csv_path = os.path.join(output_dir, f"{base_name}_96points.csv")
                self.export_to_csv(result, csv_path)
                json_path = os.path.join(output_dir, f"{base_name}_metadata.json")
                self.export_to_json(result, json_path)
                viz_path = os.path.join(output_dir, f"{base_name}_visualization.png")
                self.visualize(img, result, viz_path)

        except Exception as e:
            print(f"[ERROR] 处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
            result.warnings.append(f"处理异常: {str(e)}")

        _cb(100, "处理完成")
        result.processing_time = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"[DONE] 处理完成")
        print(f"  耗时: {result.processing_time:.2f}秒")
        if self.panel_results:
            print(f"  面板数: {len(self.panel_results)}")
            for r in self.panel_results:
                names = ",".join(c.name for c in r.curves if c.is_valid)
                csv_name = (os.path.basename(r.output_csv)
                            if r.output_csv else "(CSV被拒绝)")
                print(f"    - {csv_name} | "
                      f"置信度{r.confidence:.0%} | 曲线: {names or '无'}")
        else:
            print(f"  置信度: {result.confidence:.2%}")
            print(f"  曲线数: {len(result.curves)}")
        print(f"  警告: {len(result.warnings)}条")
        if result.warnings:
            for w in result.warnings:
                print(f"    ⚠ {w}")
        print(f"{'='*60}\n")

        return result


# ==============================================================================
# 批量处理Agent
# ==============================================================================

class BatchChartExtractorAgent:
    """批量图表提取Agent"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_CONFIG
        self.extractor = ChartExtractorAgent(self.config)

    def process_directory(self, input_dir: str, output_dir: str, 
                          pattern: str = "*.png") -> List[ExtractionResult]:
        """批量处理目录中的图片"""
        import glob

        image_paths = glob.glob(os.path.join(input_dir, pattern))
        image_paths += glob.glob(os.path.join(input_dir, "*.jpg"))
        image_paths += glob.glob(os.path.join(input_dir, "*.jpeg"))
        image_paths += glob.glob(os.path.join(input_dir, "*.bmp"))

        # 去重
        image_paths = list(set(image_paths))
        image_paths.sort()

        print(f"[INFO] 发现 {len(image_paths)} 张图片待处理")

        results = []
        for i, path in enumerate(image_paths, 1):
            print(f"\n[批量] ({i}/{len(image_paths)}) 处理: {path}")
            result = self.extractor.process(path, output_dir)
            results.append(result)

        # 汇总报告
        self._generate_summary(results, output_dir)

        return results

    def _generate_summary(self, results: List[ExtractionResult], output_dir: str):
        """生成批量处理汇总报告"""
        summary = {
            "total": len(results),
            "successful": sum(1 for r in results if r.confidence > 0.5),
            "failed": sum(1 for r in results if r.confidence <= 0.5),
            "avg_confidence": np.mean([r.confidence for r in results]),
            "avg_time": np.mean([r.processing_time for r in results]),
            "details": [
                {
                    "image": r.image_path,
                    "confidence": r.confidence,
                    "curves": len(r.curves),
                    "time": r.processing_time,
                    "warnings": r.warnings
                }
                for r in results
            ]
        }

        report_path = os.path.join(output_dir, "batch_summary.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n[汇总] 批量处理报告: {report_path}")
        print(f"  总计: {summary['total']}")
        print(f"  成功: {summary['successful']}")
        print(f"  失败: {summary['failed']}")
        print(f"  平均置信度: {summary['avg_confidence']:.2%}")
        print(f"  平均耗时: {summary['avg_time']:.2f}秒")


    def to_web_dict(self, result: ExtractionResult) -> dict:
        """将提取结果转换为Web API标准格式"""
        curves = []
        for c in result.curves:
            if not c.is_valid or not c.points:
                continue
            curves.append({
                "name": c.name,
                "color": c.color_name,
                "points": [{"x": round(p[0], 4), "y": round(p[1], 2)} for p in c.points],
                "confidence": round(c.confidence, 2)
            })

        # 生成CSV文本（不写入文件）
        csv_text = ""
        if curves:
            n = self.config["chart"]["output_points"]
            times = []
            for i in range(1, n + 1):
                total_min = i * 15
                hh, mm = total_min // 60, total_min % 60
                times.append("24:00" if hh == 24 else f"{hh:02d}:{mm:02d}")
            data = {"时点": list(range(1, n+1)), "时间": times}
            for c in curves:
                pts = c["points"]
                if len(pts) == n:
                    data[c["name"]] = [p["y"] for p in pts]
                elif len(pts) > 0:
                    xs = [p["x"] for p in pts]
                    ys = [p["y"] for p in pts]
                    x_target = (np.arange(n) + 1) * (24.0 / n)
                    y_interp = np.interp(x_target, xs, ys)
                    data[c["name"]] = [round(y, 2) for y in y_interp]
            df = pd.DataFrame(data)
            csv_text = df.to_csv(index=False, encoding='utf-8-sig')

        return {
            "success": True,
            "image_size": {
                "width": result.chart_roi[2] if result.chart_roi else 0,
                "height": result.chart_roi[3] if result.chart_roi else 0
            },
            "panels": [{"name": getattr(r, 'panel_subtype', 'unknown'), 
                       "rect": r.chart_roi,
                       "axis": {"x": [r.axis_info.x_min, r.axis_info.x_max],
                               "y": [r.axis_info.y_min, r.axis_info.y_max]}} 
                      for r in self.panel_results] if self.panel_results else [],
            "curves": curves,
            "csv_data": csv_text,
            "total_curves": len(curves),
            "processing_time": round(result.processing_time, 2),
            "warnings": result.warnings
        }

# ==============================================================================
# 命令行入口
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="全自动图表数据识别Agent - 提取图片中的文字、数字、XY轴曲线数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单张图片处理
  python shandong_chart_extractor_agent.py -i "日前出清电价.png" -o ./output

  # 批量处理目录
  python shandong_chart_extractor_agent.py -d ./screenshots -o ./output --batch

  # 指定输出96点CSV
  python shandong_chart_extractor_agent.py -i "负荷曲线.jpg" -o ./output --points 96

  # 使用GPU加速OCR
  python shandong_chart_extractor_agent.py -i "电价图.png" -o ./output --gpu
        """
    )

    parser.add_argument("-i", "--image", type=str, help="输入图片路径")
    parser.add_argument("-d", "--directory", type=str, help="输入图片目录（批量模式）")
    parser.add_argument("-o", "--output", type=str, default="./output", help="输出目录")
    parser.add_argument("--batch", action="store_true", help="批量处理模式")
    parser.add_argument("--points", type=int, default=96, help="输出点数（默认96）")
    parser.add_argument("--gpu", action="store_true", help="使用GPU加速OCR")
    parser.add_argument("--config", type=str, help="自定义配置文件路径(JSON)")

    args = parser.parse_args()

    # 版本横幅（核对是否运行了最新文件）
    print(f"[INFO] 脚本版本: {SCRIPT_VERSION} | 路径: {os.path.abspath(__file__)}")

    # 加载配置
    config = DEFAULT_CONFIG.copy()
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            custom = json.load(f)
            config.update(custom)

    config["chart"]["output_points"] = args.points
    config["ocr"]["use_gpu"] = args.gpu

    # 执行
    if args.batch or args.directory:
        if not args.directory:
            print("[ERROR] 批量模式请使用 -d/--directory 指定输入目录")
            return
        agent = BatchChartExtractorAgent(config)
        agent.process_directory(args.directory, args.output)
    else:
        if not args.image:
            print("[ERROR] 请使用 -i/--image 指定输入图片（批量处理请用 -d 指定目录）")
            return
        if not os.path.exists(args.image):
            print(f"[ERROR] 输入图片不存在: {args.image}")
            return
        agent = ChartExtractorAgent(config)
        agent.process(args.image, args.output)


if __name__ == "__main__":
    main()
