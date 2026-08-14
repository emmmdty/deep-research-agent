## Executive Summary

- 2026-08-15杭州到东莞共有8个高铁车次
- D3123次列车07:20从杭州东出发，18:00到达东莞南，历时10小时40分钟，二等座626元，一等座1001元 [1]
- D3123次列车07:20从杭州东出发，18:22到达东莞站，历时11时2分，二等座662元，一等座1043元
- 12306官方购票渠道为铁路12306网站（kyfw.12306.cn）及12306手机APP，支持扫码登录购票。
- 铁路12306每日5:00至次日1:00（周二为5:00至24:00）提供购票、改签、变更到站业务办理，全天均可办理退票等其他服务。

## Findings

### 1. [1] [6] 杭州至东莞铁路车次概况

2026-08-15杭州到东莞共有8个高铁车次（claims 01, 14, 41, 69）。首班高铁为07:20，末班车为21:10（claims 15, 42, research-04-2026-7-5-12306:19）。

杭州至东莞的列车从不同车站出发，到达不同站点：
- 杭州东到东莞南：D3123/D3122、D913/D912、D4913/D4912（qualified）、G4899（research-04-2026-7-5-12306:13）
- 杭州东到东莞站：D3123/D3122
- 杭州东到虎门：D931
- 杭州西到东莞南：G3023、G901
- 杭州南到东莞东：T101、D21、T211

各站车次分布：杭州西站到东莞南站有3列列车，杭州东站到东莞南站有2列，杭州南站到东莞东站有2列，杭州东站到虎门站有1列（research-04-2026-7-5-12306:15）。

### 2. D3123次列车信息矛盾

D3123次列车存在多个相互矛盾的描述：

**到达时间与站点矛盾：**
- 07:20从杭州东出发，18:00到达东莞南，历时10小时40分钟（claims 02, 56）
- 07:20从杭州东出发，18:22到达东莞站，历时11时2分（claims 03, 57）
- D3123/D3122次：07:20从杭州东站出发，18:22到达东莞站，经停27站（claims 09, research-03-2026-g60-g15:18, research-04-2026-7-5-12306:16）
- D3123/D3122次：07:20从杭州东站出发，18:00到达东莞南站，历时10小时40分钟，经停26站，距离1434km（claims 10, research-03-2026-g60-g15:19）

**票价矛盾：**
- 二等座626元，一等座1001元（claims 02, 56）
- 二等座662元，一等座1043元（claims 03, 57）
- 二等座704元，一等座1110元（claim 09, research-03-2026-g60-g15:18）
- 二等座668元，一等座1068元（claim 10, research-03-2026-g60-g15:19）

### 3. D913次列车信息矛盾

D913次列车票价存在矛盾：
- 二等座523元，动卧720元，无座523元（claims 25, 26）
- 二等座515元，动卧740元，高级动卧1490元（claim 61, research-04-2026-7-5-12306:22）
- D913/D912次：二等座668元，软卧上1061元，软卧下1194元（claim 11, research-03-2026-g60-g15:20）

到达时间方面：21:10从杭州东出发，9时49分到达东莞南（claims 25, 61）；D913/D912次21:10出发，07:01到达（claims 11, research-03-2026-g60-g15:20）；另有来源显示06:59+1到达（research-04-2026-7-5-12306:22）。

### 4. 其他直达车次信息

**G3023次高铁**（杭州西→东莞南）：10:13出发，9时33分到达，二等座742.5元，一等座1210.5元，商务座2488元，无座742.5元（claims 27, 28, 58, research-03-2026-g60-g15:21, 29, 30）。到达时间有19:46（research-03-2026-g60-g15:29）的记录。

**G901次高铁**（杭州西→东莞南）：15:05出发，6时4分到达，21:09到达，二等座750元，一等座1200元，商务座2475元，无座750元（claims 29, 30, 59, research-03-2026-g60-g15:24, 33）。另有来源显示G901次15:05从杭州西出发，20:51到达惠州北（claim 05）。

**D931次动车**（杭州东→虎门）：20:59出发，9时45分到达，次日06:44到达，二等座523元，动卧720元，无座523元（claims 31, 32, 60, research-03-2026-g60-g15:25, 34）。

**T101次列车**（杭州南→东莞东）：14:33出发，16时9分到达，次日06:42到达，硬座195.5元，硬卧330.5元，软卧517.5元，无座195.5元（claims 37, 62, research-03-2026-g60-g15:22, 31）。

**D21次列车**（杭州南→东莞东）：14:40出发，14时9分到达，次日04:49到达，二等座266元，二等卧432元，一等卧673元，无座266元（claims 38, 63, research-03-2026-g60-g15:23, 32）。

**T211次列车**（杭州南→东莞东）：次日05:27到达，硬座195.5元，硬卧354.5元，软卧540.5元（claim 39）。

**G4899次列车**（杭州东→东莞南）：21:15发车，07:46到达，历时10小时37分钟，经停2站（research-04-2026-7-5-12306:13）；二等座票价783元，特等/商务座1409元，软卧上2127元，软卧下2393元（research-04-2026-7-5-12306:14）。

### 5. 中转方案

多个中转方案经惠州北或东莞南换乘：

- **方案1**：G3087次14:12从杭州西出发，20:08到达惠州北（二等座701元，一等座1121元，商务座2304元），换乘19分钟后转G2747次20:27从惠州北出发，20:43到达东莞南（二等座32元，一等座51元，商务座111元），全程6时31分（claims 33, 34, 35, 64, research-04-2026-7-5-12306:23, 24）。
- **方案2**：G901次15:05从杭州西出发，20:51到达惠州北（二等座718元），换乘20分钟后转G2775次21:11从惠州北出发，21:27到达东莞南（二等座32元，一等座51元），全程6时22分（claims 06, 36, 65）。
- **方案3**：G3073次08:56从杭州西出发，14:59到达惠州北（二等座700元，一等座1119元），换乘38分钟后转G2735次15:37从惠州北出发，16:00到达东莞南（二等座32元，一等座51元），全程7时4分（claims 07, 08, 66）。
- **方案4**：G901次15:05从杭州西出发，21:09到达东莞南（二等座750元），换乘34分钟后转G6564次21:43从东莞南出发，22:06到达东莞（二等座47元，一等座59元），全程7时1分（claim 67）。
- **方案5**：G1305次08:07从杭州西出发，13:45到达惠州北（二等座676元，一等座1081元），换乘1时52分后转G2735次15:37从惠州北出发，16:00到达东莞南（二等座32元，一等座51元），全程7时53分（claim 68）。

### 6. 票价范围

杭州至东莞高铁票价约为HK$227.48至HK$2,894.95（claims 13, research-04-2026-7-5-12306:17）；杭州东至东莞南票价约为HK$227.44至HK$2,894.44（claim 40）。杭州去东莞高铁火车票价格低至HK$227.48（research-03-2026-g60-g15:26）。

### 7. 12306购票渠道与服务

12306官方购票渠道为铁路12306网站（kyfw.12306.cn）及12306手机APP，支持扫码登录购票（claim 16）。每日5:00至次日1:00（周二为5:00至24:00）提供购票、改签、变更到站业务办理，全天均可办理退票等其他服务（claim 17）。

在12306查询杭州西至东莞南的车次时，如果查询结果中没有满足需求的车次，可以使用中转换乘功能（claim 18）。12306显示的价格均为实际活动折扣后票价，具体票价以确认支付时实际购买的铺别票价为准（claim 19）。如因运力原因或其他不可控因素导致列车调度调整时，当前车型可能会发生变动（claim 20）。

12306查询结果将显示相关的车次、出发/到达时间、车程时间及车厢等级的剩余座位信息（claim 49）。12306网站及线上票务平台以人民币票价发售车票（claims 50, 51）。预售期第15天的车票发售时间因应出发站有所不同（claim 52）。旅客可在12306手机App为发售第15天但未到开售时间的车票，预先选择车次、车厢等级及乘车人，预填资料保留至开售后30分钟（claim 53）。

使用居民身份证购票的，可凭购票时所使用的乘车人有效居民身份证原件到车站售票窗口、铁路客票代售点或车站自动售票机上办理换票（claim 54）。有效身份证件信息、订单号码等不一致的，不能换票（claim 55）。

车票售罄时可先用12306候补，再比较前后班次、同城其他车站或中途转乘（claim 43）。不要为了上车刻意买错乘车区间（claim 44）。行程变动时，退票与改签费用会受办理时间、原车票与新车票条件影响（claim 45）。

台湾人可以用台胞证在12306买高铁票（claim 46）。2026年台湾旅客搭大陆高铁，最重要的是用有效台胞证完成实名购票（claim 47）。

### 8. 学生优惠票政策

学生旅客每学年（10月1日至次年9月30日）享有4次单程优惠票，可随时使用（claims research-04-2026-7-5-12306:26, 45）。学生优惠票使用不再限于寒暑假期，可在每学年内随时使用（claims research-04-2026-7-5-12306:31, 46）。

动车组列车学生优惠票适用范围扩大至二等座、一等座和卧铺各席别（claims research-04-2026-7-5-12306:28, 49）。动车组学生票按执行票价7.5折计算，相当于"折上折"，最低可达公布票价4折（claims research-04-2026-7-5-12306:03, 29, 34, 51）。普速列车学生票维持现行政策，硬座5折、硬卧加收硬卧与硬座全价差额（claims research-04-2026-7-5-12306:04, 35, 50, 52）。

学生优惠区间可根据家庭居住地至学校所在地调整设置，院校所在地须与学信网信息一致，家庭居住地可根据实际变动情况设置，修改次数不限（claims research-04-2026-7-5-12306:02, 27, 33, 48）。

学生每学年乘车前应在线完成学生优惠资质核验或到车站指定售票窗口或自动售票机办理一次本人居民身份证件与火车票学生优惠卡的优惠资质核验手续（claim research-04-2026-7-5-12306:09）。火车票学生优惠卡内需载明学生姓名、有效身份证件号码、优惠乘车区间、入学日期、优惠乘车次数等信息（claim research-04-2026-7-5-12306:10）。应有而没有"火车票学生优惠卡"，或卡内信息不全、不能识别或与学生证记载不一致的，不发售学生优惠票（claim research-04-2026-7-5-12306:11）。

在校学生已通过优惠资质核验的，出行时铁路部门将不再查验学生证；未通过优惠资质核验的，仍需携带学生证乘车（claims research-04-2026-7-5-12306:37, 54）。入学新生可凭录取通知书线上、线下购买学生优惠票出行（claims research-04-2026-7-5-12306:38, 55）。

铁路12306客户端学生预约购票服务实现常态化运行，开放时间从寒暑假期拓展至全年（claims research-04-2026-7-5-12306:05, 36, 53）。符合条件学生可在开车前20天至17天提报预约需求（claims research-04-2026-7-5-12306:06, 36, 53）。2026年春运期间，学生旅客可在开车前第20天5时至第17天23时提报预约需求，同一账户最多可同时提交3个订单，每个订单可提交同一乘车日期的5个"车次+席别"的组合（claim research-04-2026-7-5-12306:07）。在校学生最多可为包含本人在内的19名学生旅客预约（claim research-04-2026-7-5-12306:08）。

学生优惠票退票后返还优惠次数（claims research-04-2026-7-5-12306:01, 32, 47）。在减价优惠区间内购买联程车票时，开车时间在5天以内的扣减1次优惠次数（claim research-04-2026-7-5-12306:12）。

相关优惠车票预计将于9月6日开始发售（claims research-04-2026-7-5-12306:30, 39, 56）。学生旅客可通过铁路12306网站、客户端、微信等渠道查询（claims research-04-2026-7-5-12306:40, 57）。

12306购票系统在选择乘车人时，若当前选择的优先席别有不支持学生票的，会提示是否选择购买成人票（claim research-04-2026-7-5-12306:25）。

### 9. [73,79] 儿童票政策

除需通勤上学的学生，以及已获铁路公司同意照顾的情况外，14岁以下儿童搭乘由杭州至东莞的高铁必须由成人陪同（claim research-04-2026-7-5-12306:20）。小童票适用于出行当日年满6至13岁的乘客，年龄将以实际乘车日期计算（claim research-04-2026-7-5-12306:21）。

### 10. 杭州至东莞自驾信息

从杭州到东莞自驾总距离为1288.1公里（claims research-03-2026-g60-g15:05, 38），总耗时为15.5小时（claims research-03-2026-g60-g15:06, 39），油费为773元（claims research-03-2026-g60-g15:07, 40），路桥费为630元（claims research-03-2026-g60-g15:08, 41），总费用为1403元（claims research-03-2026-g60-g15:09, 42）。

途经的高速包括杭新景高速、长深高速、龙丽温高速、沪昆高速、济广高速、厦蓉高速、赣州绕城高速、大广高速、龙河高速、珠三角环线高速等（claims research-03-2026-g60-g15:10, 43）。具体经过沪昆高速公路（G60）（claim research-03-2026-g60-g15:44）、长深高速公路（G25）（claim research-03-2026-g60-g15:45）、大广高速公路（claim research-03-2026-g60-g15:46）、济广高速公路（claim research-03-2026-g60-g15:47）、珠三角环线高速公路（G94）（claim research-03-2026-g60-g15:48）、龙河高速公路（claim research-03-2026-g60-g15:49）、厦蓉高速公路（claim research-03-2026-g60-g15:50）、赣州绕城高速公路（claim research-03-2026-g60-g15:51）。

沪昆高速（G60）起于上海市闵行区沪闵路立交，终点止于云南省昆明市盘龙区小庄立交，全长2353千米（claim research-03-2026-g60-g15:11），途经浙江省的杭州市、嘉兴市、金华市、衢州市（claim research-03-2026-g60-g15:12），是中国国家高速公路网18条东西横向干线的第13条（claim research-03-2026-g60-g15:13）。

分段收费信息：杭新景高速收费138公里（claim research-03-2026-g60-g15:14），杭新龙高速收费32.7公里（claim research-03-2026-g60-g15:15），杭金衢高速收费82.6公里（claim research-03-2026-g60-g15:16），浙赣收费站处上沪昆高速收费18.0公里（claim research-03-2026-g60-g15:17）。

### 11. 杭州至广州航班信息

从杭州到广州的往返机票858元起，单程机票399元起（claim research-02-2026:01）。已找到的最优惠航班为859元（claim research-02-2026:02）。票价最优惠的月份是九月（claim research-02-2026:03）。

从杭州到广州的平均飞行时间为2小时19分钟（claim research-02-2026:04），另有来源显示约需2小时16分钟（claim research-02-2026:07）。最受欢迎的航空公司是四川航空（claim research-02-2026:05）。每周平均航班数为413班（claim research-02-2026:06）。

提供杭州飞广州航班的航空公司包括Air China、Shanghai Airlines、Sichuan Airlines、China Eastern Airlines、China Southern Airlines（claim research-02-2026:09），另有来源补充还包括Xiamen Airlines、9 Air、Hainan Airlines、Beijing Capital Airlines（claim research-02-2026:10）。

2026年9月3日杭州到广州的机票价格为RM 356（claim research-02-2026:11）。ANA目前运行东京羽田、成田、大阪关西机场与北京、上海（虹桥/浦东）、广州、深圳、大连、青岛、杭州之间的往返航班（claim research-02-2026:12）。

杭州萧山机场有飞往深圳宝安的航班：CZ3570，计划时间1130-1345，机型JET（claim research-02-2026:33）；HU7394，机型78A，计划时间1155-1425（claim research-02-2026:34）。

### 12. [30] 东莞至深圳宝安机场交通

从东莞市到深圳宝安国际机场(SZX)的驾驶距离为36英里，开车大约需要52分钟（claim research-02-2026:13）。乘坐出租车约35.5英里，耗时52分钟，估计价格26–32美元（claim research-02-2026:14）。

从东莞市到深圳宝安国际机场的火车客运服务由Dongguan Rail Transit运营，到达Humen Station车站（claim research-02-2026:15）。

深圳机场汽车站到东莞万江的豪华大巴票价为45.00元，发车时间从8:00开始，包括8:00、9:00、9:30、10:00、10:30、11:10、11:50、12:30、13:10、13:50等班次（claim research-02-2026:16）。

深圳宝安国际机场的城际大巴运营线包括香港、澳门、惠州、惠东、中山、东莞城市、东莞石龙、东莞大朗、东莞清溪、惠阳（claim research-02-2026:17）。

深圳宝安国际机场出租车夜间附加费为23:00至次日06:00，起步价升至13元且加收20%（claim research-02-2026:18）。等候费为0.8元/分钟，大件行李费为0.5元/件（体积＞0.2立方米、重量＞20千克）（claim research-02-2026:19）。

东莞城区到深圳宝安国际机场的大巴首车时间为7:20，末班时间为19:20（claim research-02-2026:20）。

### 13. 广州白云机场至东莞交通

从广州白云国际机场到东莞市的最便宜方式是地铁2号线和火车，花费5-9美元，需要2小时19分钟（claim research-02-2026:21）。最快方式是开车，花费10-15美元，需要1小时1分钟（claim research-02-2026:22）。

从广州白云国际机场到东莞市没有直达巴士，但客运服务从Guangzhou Baiyun Airport出发，经过Dongguan Shilong到达Guangzhou Municipal，旅程（包括转乘）大约需要3小时15分钟（claim research-02-2026:23）。没有直达火车，但客运服务从Guangzhou Airport South出发，经过Hongfu Road到达Guangzhou East和Guangdong（claim research-02-2026:24）。

广州白云机场到东莞的机场大巴部分班次预计车程为80分钟，发车时间包括00:50、07:40、08:10、08:50、09:30、10:00、10:40、11:20、12:00、12:40、13:20、13:50、14:30、15:00、15:40、16:20、17:00、17:40、18:20、19:00、19:50、20:40、21:30、22:30、23:30（claim research-02-2026:25）。部分班次预计车程为120分钟，发车时间包括09:10、10:20、11:30、12:30、13:30、14:20、15:30、16:40、17:50、18:50、19:40、20:30（claim research-02-2026:26）。

白云机场空港快线大巴新增"东莞南城"线路，每天往返56个班次，约30分钟发一班车，单程行车时间约75分钟，票价52元（claim research-02-2026:27）。首班车为07:30，末班车为23:50（claim research-02-2026:28）。东莞南城候机楼地址为东莞市东莞大道宏成五金城1号，电话0769-23151111（claim research-02-2026:29）。

2025年10月30日12时，广州白云国际机场T3航站楼正式启用，东方航空、上海航空、中国联合航空、吉祥航空、奥捷航空将首批入驻（claim research-02-2026:30）。自西平西站出发，最快仅需57分钟即可抵达白云机场东站（T3）（claim research-02-2026:31）。东莞全市共有12个城轨站点可直达白云机场（claim research-02-2026:32）。

### 14. 深圳横岗长途汽车客运站至东莞班次

深圳横岗长途汽车客运站有发往东莞的班次，发车时间包括7:45、9:10、10:00、11:30、13:00、14:10、15:40、16:20、18:05，票价均为55元，车型为大型高一座（claims research-03-2026-g60-g15:01, 35, 36）。车站地址为深圳市龙岗区横岗镇深惠公路荷坳牛奶公司旁，联系电话28625268（claims research-03-2026-g60-g15:02, 37）。

### 15. 巴巴快巴汽车票服务

巴巴快巴提供汽车票网上订票服务，帮助热线为400-96520-88（claim research-03-2026-g60-g15:03）。平台提供杭州各大汽车站至浙江省内及上海、江苏省、安徽省等地的部分线路票价调整公告（claim research-03-2026-g60-g15:04）。

### 16. 长龙航空畅飞卡产品

长龙航空"365畅飞卡"售价365元，下单后即可兑换经济舱M舱机票，不限次数，每次仅需再支付266元（claims research-05-e6e6c72f9185:01, 08, 31, 41, 51, 59）。"365畅飞卡PLUS"版本售价2345元，除普通版本的兑换权益外，额外享经济舱其他舱位8折优惠（claims research-05-e6e6c72f9185:02, 09, 35, 42, 52, 58）。

畅飞卡一年时间内（2025年10月26日至2026年10月24日，特殊日期除外）都可兑换长龙航空国内自营航线（claims research-05-e6e6c72f9185:04, 11, 32, 43, 53）。首次实现换票无时段限制、全天均可飞（claims research-05-e6e6c72f9185:03, 10, 33, 36, 43, 54）。365元版本屏蔽了少数特殊航线（杭州=广州/哈尔滨/沈阳/长春/大连/贵阳）（claim research-05-e6e6c72f9185:56）。

畅飞卡于10月19日在京东旅行限时开售，销售时间为10月19日10点至11月11日24点（claims research-05-e6e6c72f9185:06, 49）。京东旅行联合长龙航空推出"365畅飞卡"，价格仅365元，刷新行业纪录（claim research-05-e6e6c72f9185:37）。

长龙航空总部在杭州，江浙沪地区航线密集，共有100多条航线辐射全国（claims research-05-e6e6c72f9185:05, 12, 34, 44, 55）。拥有73架客机、100+国内航线，覆盖杭州、宁波、温州、哈尔滨、长春、银川、广州、深圳、成都等城市（claims research-05-e6e6c72f9185:24, 57）。2022年夏航季执飞国内航线130余条，通达国内城市近90余座（claim research-05-e6e6c72f9185:19）。2026年夏航季（3月29日起）预计执飞航线144条，其中国内航线125条，国际及地区航线19条（claim research-05-e6e6c72f9185:60）。

长龙航空作为浙江省主基地航空公司，在新航季共执飞浙江省内进出港航线93条，其中国内航线84条，通达北京、广州、深圳、成都、西安、重庆、丽江等主要旅游城市（claims research-05-e6e6c72f9185:26, 61）。航线覆盖广州和深圳，因此畅飞卡可用于杭州往返广州或深圳（claim research-05-e6e6c72f9185:25）。近期通航的城市包括重庆、西安、武汉、广州、深圳、成都等（claim research-05-e6e6c72f9185:28）。

长龙航空推出畅飞卡系列、商旅卡等权益类产品，兼顾灵活性与性价比（claims research-05-e6e6c72f9185:27, 62）。构建以杭州为中心的全国4小时交通圈（claim research-05-e6e6c72f9185:29）。最热门的机场是杭州（claim research-05-e6e6c72f9185:46），目的地数量为83个（claim research-05-e6e6c72f9185:47）。

长龙航空有从广州到喀什的航线，经停郑州（claim research-05-e6e6c72f9185:14）。广州去乌鲁木齐没有航线，但有到喀什的航线（claim research-05-e6e6c72f9185:15）。

长龙航空7月1日起正式发售"长龙自由GO"旅行卡产品（claim research-05-e6e6c72f9185:16）。支付现金4999元，即可额外获得1000元，卡内可用额度共计5999元（claim research-05-e6e6c72f9185:17）。适用长龙航空所有国内自营航班（claim research-05-e6e6c72f9185:18）。使用时间自由，节假日及出行高峰期均可以使用（claim research-05-e6e6c72f9185:20）。

长龙航空多次卡产品价格499元/899元/1299元（一套），不同航线对应不同价位组，产品价格均不含民航发展基金和燃油附加费（claim research-05-e6e6c72f9185:38）。权益为在适用范围内享受2次经济舱单程飞行权益（claim research-05-e6e6c72f9185:39）。适用航班为长龙航空指定国内自营航班，其中港澳台地区航班、包机以及代码共享航班除外（claim research-05-e6e6c72f9185:40）。

**Qualified claim**：长龙航空365畅飞卡国内部分卡目前无法使用（claim research-05-e6e6c72f9185:13，qualified）。

### 17. 广州南站换乘服务

广州南站试行铁路出站换乘地铁"单向免检"，并启用一层南端便捷换乘区域等便民服务新举措，帮助旅客节省中转换乘时间（claim 23）。购买了联程车票的旅客，到广州南站后可乘坐站台南端出站扶梯到达一楼南侧进行换乘（claim 24）。

### 18. Trip.com服务

Trip.com提供由杭州前往东莞的高铁订票、时间表及票价查询服务（claim 21），也提供由深圳北前往东莞的高铁订票、时间表及票价查询服务（claim 22）。

## Evidence Status

**矛盾点汇总：**

1. **D3123次列车到达信息矛盾**：到达站（东莞南 vs 东莞站）、到达时间（18:00 vs 18:22）、历时（10小时40分钟 vs 11时2分）、经停站数（26 vs 27站）、票价（二等座626/662/668/704元，一等座1001/1043/1068/1110元）均存在多个版本。这些差异可能源于同一车次在不同日期或不同查询条件下的票价浮动，以及到达不同站点（东莞南 vs 东莞站）的差异，但来源未明确说明。

2. **D913次列车票价矛盾**：二等座523元 vs 515元，动卧720元 vs 740元，且部分来源显示有高级动卧1490元，另有来源显示软卧上1061元、软卧下1194元。到达时间也有06:59+1和07:01两个版本。

3. **G901次列车到达站矛盾**：部分来源显示G901次15:05从杭州西出发直达东莞南（21:09到达），另有来源显示其20:51到达惠州北（作为中转方案的一部分）。

4. **D4913/D4912次列车**：该车次信息被标记为qualified（research-03-2026-g60-g15:28），需谨慎对待。

5. **长龙航空畅飞卡**：存在一条qualified claim（research-05-e6e6c72f9185:13），指出"国内部分卡目前无法使用"，与畅飞卡正常销售使用的信息存在潜在冲突，需进一步核实。

6. **杭州至广州航班信息**：平均飞行时间有2小时19分钟和2小时16分钟两个版本；最优惠票价有858元和859元两个版本。

7. **杭州至东莞车次数量**：多个来源一致确认8个车次，但具体车次清单在不同来源间存在差异（如G4899次仅在一个来源中出现）。

8. **D3123/D3122与D3123的关系**：部分来源将车次标注为"D3123/D3122"，部分仅标注"D3123"，可能为同一列车在不同区段的复用车次。

其余信息在各来源间保持一致，未发现其他矛盾。

## References

1. 杭州到东莞高铁查询 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/gaotie (document: web_search-e4abe537fdfbf382)
2. 杭州到东莞动车查询-动车票价-动车时刻表-[携程]火车票网上订票官网 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/dongche (document: web_search-cc3c937e4d9bddd1)
3. 杭州东到东莞列车时刻表票价 - 高铁旅行 — https://www.gaotie.com.cn/lieche/hangzhoudong-dongguan.html (document: web_search-26d66072379cb0f0)
4. 杭州去東莞高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhou-to-dongguan (document: web_search-d5a63c303dfeb262)
5. 深圳北去東莞高鐵訂票、時間表及票價查詢 - Trip.com — https://hk.trip.com/trains/china/route/shenzhen-north-to-dongguan (document: web_search-bd41d1d40f2648a1)
6. 火车票 — https://kyfw.12306.cn/otn/leftTicket/init (document: web_search-8de5e16f387cf4d9)
7. 中国铁路12306网站 — https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc&fs=%E6%9D%AD%E5%B7%9E%E8%A5%BF%2CHVU&ts=%E4%B8%9C%E8%8E%9E%E5%8D%97%2CDNA&date=2026-08-07&flag=N%2CN%2CY (document: web_search-bf410a6069191fc6)
8. 广州市交通运输局网站 - 广州南站多方式换乘接驳更便捷 — http://jtj.gz.gov.cn/xwdt/gzdt/content/post_7104854.html (document: web_search-d34acdd468ce3626)
9. 杭州东到东莞火车票预订与代购 — https://trains.ctrip.com/trainbooking/hangzhoudong-dongguan2 (document: web_search-988d2ab441d72039)
10. 杭州到东莞高铁查询 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/gaotie (document: web_search-9a53ae3c75eb5dc7)
11. 杭州西到东莞南直达车次查询- 列车时刻表 — https://train.hao86.com/%E6%9D%AD%E5%B7%9E%E8%A5%BF-%E4%B8%9C%E8%8E%9E%E5%8D%97 (document: web_search-364447ded5bfecab)
12. 杭州東去東莞南高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhoudong-to-dongguannan (document: web_search-564af896eaa6f08e)
13. 2026 大陸高鐵攻略｜台胞證買票、12306、座位、行李與進站流程 - GO CHINA 大陸包車 — https://gochina.com.tw/taking-chinas-high-speed-rail-and-trains (document: web_search-5b79238c4fbf2aea)
14. 2026高鐵 12306 攻略 — https://hk.trip.com/blog/12306 (document: web_search-e6e4ae0b082ac05e)
15. 高速鐵路> 於12306購票 - 高鐵 — https://www.highspeed.mtr.com.hk/tc/latest-news/ticketing-via-12306-purchase-ticket.html (document: web_search-51f6dbe58cd89222)
16. 中国铁路12306网站 — https://kyfw.12306.cn/otn/gonggao/changeToPaperTicket.html (document: web_search-23cc7e1c7c7551ee)
17. 杭州东到东莞火车票预订与代购 — https://trains.ctrip.com/trainbooking/hangzhoudong-dongguan2 (document: web_search-12d0586b25af465d)
18. 杭州到东莞高铁查询-高铁票价-高铁时刻表-[携程]高铁票订票官网 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/gaotie (document: fetch_page-e5be6a0548852588)
19. 杭州到东莞高铁查询-高铁票价-高铁时刻表-[携程]高铁票订票官网 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/gaotie (document: fetch_page-de6de0fbe11fe322)
20. 杭州东到东莞列车时刻表票价查询-【新版】-杭州东到东莞高铁时刻表查询火车票预订 — https://www.gaotie.com.cn/lieche/hangzhoudong-dongguan.html (document: fetch_page-b27dd0e68faf2f02)
21. 杭州东到东莞火车票预订与代购-高铁票价,动车票价-高铁订票,动车订票网-携程火车票订购中心 — https://trains.ctrip.com/trainbooking/hangzhoudong-dongguan2 (document: fetch_page-e135061d15f45627)
22. 杭州东到东莞火车票预订与代购-高铁票价,动车票价-高铁订票,动车订票网-携程火车票订购中心 — https://trains.ctrip.com/trainbooking/hangzhoudong-dongguan2 (document: fetch_page-e540474f7c4b2be2)
23. 从杭州出发前往深圳的特价机票 - 机票预订 — https://www.tianxun.com/routes/hgh/szx/hangzhou-to-shenzhen-bao-an-international.html (document: web_search-7aeb64dede75a30e)
24. 杭州- 深圳 — https://hk.ch.com/HGH-SZX (document: web_search-7ca994cab7daedfa)
25. 搜尋從杭州（HGH）飛往深圳（SZX）的航班 — https://www.booking.com/flights/route/city-to-city/cn-hangzhou-to-cn-shenzhen.zh-tw.html (document: web_search-6e2056f2395cd3ed)
26. Air China Limited — https://www.airchina.us/US/CN/Home (document: web_search-3a4f43d1098291e1)
27. 杭州到广州机票- 特价机票预订 - Traveloka — https://www.traveloka.com/zh-my/flight/route/Hangzhou-Guangzhou.HGH.CAN (document: web_search-148c32e343ccb864)
28. 从杭州出发前往广州的特价机票 - 机票预订 — https://www.tianxun.com/routes/hgh/can/hangzhou-to-guangzhou.html (document: web_search-53cf900bfbb0335b)
29. 預訂杭州飛廣州（HGH－CAN）的便宜機票- 航班 — https://www.booking.com/flights/route/city-to-city/cn-hangzhou-to-cn-guangzhou.zh-tw.html (document: web_search-b0fcaca2291d93bb)
30. ANA中国大陆地区航班时刻表| 推广活动 — https://www.ana.co.jp/zh/cn/plan-book/promotions/multiple-routes-flight-resumption (document: web_search-dbf19efccafb6844)
31. 通过东莞市从深圳宝安国际机场(SZX)到线2 地铁, 火车, 巴士, ... — https://www.rome2rio.com/zh/s/%E4%B8%9C%E8%8E%9E%E5%B8%82/%E6%B7%B1%E5%9C%B3%E5%AE%9D%E5%AE%89%E5%9B%BD%E9%99%85%E6%9C%BA%E5%9C%BA-SZX (document: web_search-d1195340417a10d1)
32. 深圳宝安机场到东莞万江直达大巴有几个班次？多长时间一班？（附时刻表） — https://jt.shenchuang.com/qiche2/20191025/1511307.shtml (document: web_search-8af35ab5aa387e08)
33. 机场交通 — https://www.csair.com/h5/cn/guonei/Shenzhen/1amfkv1nfbjjr.shtml (document: web_search-89e3307ca3d3aab1)
34. 深圳宝安国际机场交通 - 特价机票 — https://flights.ch.com/airports/jiaotong-SZX (document: web_search-64ea9c9f9b89400d)
35. 通过广州白云国际机场(CAN)从东莞市到线3 地铁, 火车, 巴士 ... — https://www.rome2rio.com/zh/s/%E5%B9%BF%E5%B7%9E%E7%99%BD%E4%BA%91%E5%9B%BD%E9%99%85%E6%9C%BA%E5%9C%BA-CAN/%E4%B8%9C%E8%8E%9E%E5%B8%82 (document: web_search-f2089debffea4420)
36. 广州白云机场到东莞大巴时刻表 - 本地宝 — https://m.dg.bendibao.com/traffic/143774.shtm (document: web_search-995f691f58bb7a46)
37. 白云机场空港快线大巴新增“东莞南城”线路 — https://news.carnoc.com/list/321/321727.html (document: web_search-2e6c5f42206ac1e0)
38. 东莞⇋白云机场T3航站楼全攻略，多种出行方式任你选！ — https://pub.timedg.com/s/2025-10/30/AP6902ff22e4b0b83bb5bc133a.html (document: web_search-cb26dc9aa2a2ef5f)
39. 出发航班时刻表- 杭州萧山机场门户网站 — http://www.hzairport.com/flight/leavetime/p/28.html (document: web_search-46b04de3aa1619dc)
40. 杭州去東莞高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhou-to-dongguan (document: web_search-7180096f099c4874)
41. 长途汽车时刻表及票价查询! — https://www.piaojia.cn/changtu (document: web_search-a5f59cb1e75536df)
42. 深圳横岗长途汽车客运站到东莞的汽车班次（票价+发车时间） — https://jt.shenchuang.com/qiche2/20191008/1508363.shtml (document: web_search-61b5f55db059a189)
43. 巴巴快巴:汽车票网上订票_汽车票预订_长途汽车票_网上订票_96520 — https://www.bababus.com (document: web_search-200dfbcc65fb5b14)
44. 开车从杭州到东莞多少公里-时间要多久-高速怎么走-自驾高速过路费多少钱-油费_车主手册 — https://www.icauto.com.cn/route/142_124.html (document: web_search-700a259eb18a0ffd)
45. 杭州开车到东莞路线查询- 杭州自驾网 — https://m-cha.zuzuche.com/lu/hangzhou/2047.html (document: web_search-64dc5dd324291b1b)
46. 摇车牌 - 国家高速G60：沪昆高速 — https://yaochepai.cn/article/c0i122537.html (document: web_search-28cf1627d028db2f)
47. 上海—昆明高速公路 - 维基百科 — https://zh.wikipedia.org/zh-hans/%E4%B8%8A%E6%B5%B7%E2%80%94%E6%98%86%E6%98%8E%E9%AB%98%E9%80%9F%E5%85%AC%E8%B7%AF (document: web_search-8f80c64852f7dd73)
48. 杭州去東莞高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhou-to-dongguan (document: web_search-67f919bfe9199e40)
49. 杭州到东莞东火车票预订与代购 — https://trains.ctrip.com/trainbooking/hangzhou-dongguandong (document: web_search-265c285481305dc0)
50. 杭州到东莞动车查询-动车票价-动车时刻表-[携程]火车票网上订票官网 — https://trains.ctrip.com/TrainBooking/hangzhou-dongguan2/dongche (document: web_search-89b2844a75ad3fb6)
51. 长途汽车时刻表及票价查询! — https://www.piaojia.cn/changtu (document: web_search-60cfaf3c24f5d4cd)
52. 巴巴快巴:汽车票网上订票_汽车票预订_长途汽车票_网上订票_96520 — https://www.bababus.com (document: web_search-f45a84286c60e893)
53. 深圳横岗长途汽车客运站到东莞的汽车班次（票价+发车时间） — https://jt.shenchuang.com/qiche2/20191008/1508363.shtml (document: web_search-cea2e490c76d40e6)
54. 火车票 — https://kyfw.12306.cn/otn/leftTicket/init (document: web_search-542759a7eeff770b)
55. 开车从杭州到东莞多少公里-时间要多久-高速怎么走-自驾高速过路费多少钱-油费_车主手册 — https://www.icauto.com.cn/route/142_124.html (document: fetch_page-4103c806be80611b)
56. 开车从杭州到东莞多少公里-时间要多久-高速怎么走-自驾高速过路费多少钱-油费_车主手册 — https://www.icauto.com.cn/route/142_124.html (document: fetch_page-c045e10aa07a88f8)
57. 开车从杭州到东莞多少公里-时间要多久-高速怎么走-自驾高速过路费多少钱-油费_车主手册 — https://www.icauto.com.cn/route/142_124.html (document: fetch_page-5665e4ad9a7d6b53)
58. 汽车时刻表查询,长途汽车查询,汽车票价,汽车时刻表 - 长途汽车时刻表及票价查询! — https://www.piaojia.cn/changtu/ (document: fetch_page-14eace015ec8b4b0)
59. 汽车时刻表查询,长途汽车查询,汽车票价,汽车时刻表 - 长途汽车时刻表及票价查询! — https://www.piaojia.cn/changtu/ (document: fetch_page-fccf9f1f1ea1fad4)
60. 新举措！2026届高校毕业生新增2次单程学生优惠票 — https://www.news.cn/politics/20260116/10ef3c7d07eb4f90a91421433380fbe9/c.html (document: web_search-c44b302482a2b249)
61. 铁路正式发售计价规则优化后的学生优惠票 — http://wap.china-railway.com.cn/xwzx/ywsl/202509/t20250912_148467.html (document: web_search-b6cbe316b51f8c85)
62. 学生购火车票优惠政策上新一文了解购票常见问题 — https://app.xinhuanet.com/news/article.html?articleId=6f5630c5be1ca960625fc892f62fb22a (document: web_search-f47e8a187f524a98)
63. 哪些学生可以购买学生票？ — https://kyfw.12306.cn/otn/gonggao/student.html (document: web_search-d02fc29a071ae576)
64. 通知！学生票核验最新规定 — http://m.cyol.com/gb/articles/2024-01/14/content_qbYKpdtpe6.html (document: web_search-a4cc0d9ee8cde173)
65. @即将放寒假的小伙伴们 你的火车票学生优惠资质核验了吗？-新华网 — http://www.news.cn/politics/20240114/2a81c0b538c54d41a27e85ac59b22469/c.html (document: web_search-7390b1b66c64f37c)
66. 火车票学生优惠说明 — https://gradschool.ustc.edu.cn/article/116 (document: web_search-076a5ebc63b4ad6d)
67. 火车票学生优惠使用指南 — https://sustech.online/service/student-train-ticket (document: web_search-e95fc35e2413e005)
68. 杭州东到东莞列车时刻表票价 - 高铁旅行 — https://www.gaotie.com.cn/lieche/hangzhoudong-dongguan.html (document: web_search-37ca41214d0f0131)
69. 杭州去東莞高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhou-to-dongguan (document: web_search-ee36bb1fc2b70efe)
70. 杭州到东莞东火车票预订与代购 — https://trains.ctrip.com/trainbooking/hangzhou-dongguandong (document: web_search-a3763478570c881a)
71. 中国铁路12306网站 — https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc&fs=%E6%9D%AD%E5%B7%9E%E8%A5%BF%2CHVU&ts=%E4%B8%9C%E8%8E%9E%E5%8D%97%2CDNA&date=2026-08-07&flag=N%2CN%2CY (document: web_search-87a917cd9cc5d47e)
72. 铁路部门进一步优化学生旅客购票出行优惠措施 — https://www.12306.cn/mormhweb/zxdt/202508/t20250815_44642.html (document: web_search-e1ba5e7016cff4fe)
73. 规则优化后铁路学生优惠票开售每学年4次使用不再限寒暑假 — https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/202509/t20250908_4192554.html (document: web_search-0ad34a55f2d4a9b6)
74. 杭州去東莞高鐵訂票、時間表及票價查詢 — https://hk.trip.com/trains/china/route/hangzhou-to-dongguan (document: web_search-71e784253e343706)
75. 中国铁路12306网站 — https://kyfw.12306.cn/otn/gonggao/student.html (document: fetch_page-075b687cafb1ea08)
76. 中国铁路12306网站 — https://kyfw.12306.cn/otn/gonggao/student.html (document: fetch_page-9c3e27c6eb79edab)
77. 中国铁路12306网站 — https://www.12306.cn/mormhweb/zxdt/202508/t20250815_44642.html (document: fetch_page-d8aa3c033f750bda)
78. 中国铁路12306网站 — https://www.12306.cn/mormhweb/zxdt/202508/t20250815_44642.html (document: fetch_page-9f2740dadf2353cb)
79. 规则优化后铁路学生优惠票开售 每学年4次 使用不再限寒暑假_信息提示_首都之窗_北京市人民政府门户网站 — https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/202509/t20250908_4192554.html (document: fetch_page-bde80775a6dc66f2)
80. 长龙航空365畅飞卡如何使用 — https://www.douyin.com/shipin/7564218018075527187 (document: web_search-4b2aa746111a643e)
81. 长龙航空“365畅飞卡”10月19日在京东旅行限时开售 — http://news.cnair.com/c/202510/138940.html (document: web_search-8da165dcc62a0d0b)
82. 国内随心飞历史价格新低！京东旅行10月19日限时开售长龙 ... — https://caijing.chinadaily.com.cn/a/202510/20/WS68f5c014a310c4deea5ed262.html (document: web_search-52e2a84d9fcdcd15)
83. 长龙航空7月1日正式发售“长龙自由GO”旅行卡 - 中国民航网 — http://caacnews.com.cn/1/6/202207/t20220701_1348042.html (document: web_search-2e9d73c207fa0aac)
84. 长龙航空推出超低价国内随心飞产品！📅 预约时间 — https://www.sina.cn/news/detail/5223775851514413.html (document: web_search-b6f8f2eab5850a9c)
85. 长龙航空2026夏航季新开多条航线 - 浙江新闻 — https://zjnews.zjol.com.cn/yc/qmt/202603/t20260320_31562961.shtml (document: web_search-6152e7c6878f6141)
86. 长龙航空 - 维基百科 — https://zh.wikipedia.org/zh-hans/%E9%95%BF%E9%BE%99%E8%88%AA%E7%A9%BA (document: web_search-08b90009f7e94776)
87. 预订前往杭州的长龙航空机票，往返¥889起 | Skyscanner — https://www.tianxun.com/flights/airline-flights-to-city/chgh/loong-air-gj/cheap-flights-with-loong-air-gj-flights-to-hangzhou (document: web_search-e11cb9d762a12e60)
88. 长龙航空“365畅飞卡”10月19日在京东旅行限时开售 — http://news.cnair.com/c/202510/138940.html (document: web_search-796a75666a392eb9)
89. 长龙航空多次卡 — https://m.flight.qunar.com/shark/active/41cedfbc40bc414198bb0a5b62ddec43 (document: web_search-3e3028043db83d9c)
90. “随心飞”仅365元历史新低：一口价266元机票无限 ... — https://finance.sina.com.cn/tech/discovery/2025-10-18/doc-infuihxf0338393.shtml (document: web_search-a7cc2ff7807452f0)
91. 旅客、行李运输总条件 — https://pages.c-ctrip.com/flight/h5/hybrid/booking/content/gj-transport-rule.html (document: web_search-85a550ef2d0553e6)
92. 国内随心飞历史价格新低！京东旅行10月19日限时开售长龙 ... — https://caijing.chinadaily.com.cn/a/202510/20/WS68f5c014a310c4deea5ed262.html (document: web_search-8cb7b850ba36961b)
93. 浙江长龙航空有限公司国内多等级舱位销售管理规定 — https://meiyacommonfile.oss-cn-shenzhen.aliyuncs.com/policy/content5230e81724231337018.pdf (document: web_search-7872afb8f657d008)
94. 旅客、行李运输总条件 — https://pages.c-ctrip.com/flight/h5/hybrid/booking/content/gj-transport-rule.html (document: web_search-cf0af8d75e0b42a9)
95. 长龙航空航班和机票 - 机票预订 — https://www.tianxun.com/airline/airline-loong-air-gj.html (document: web_search-d1dee6de24906645)
96. 全时段畅飞 全年不限次：长龙航空“365畅飞卡”10月19日在京东旅行限时开售 - 旅游焦点 - 新闻资讯 - 航空旅游网 — http://news.cnair.com/c/202510/138940.html (document: fetch_page-c6bce817e77e7d66)
97. 🚀 下半年旅行必备！长龙航空「随心飞」上线啦下半年规划旅行时，“随心飞”已经成为国内出游绕不开的选项。最近，又一家航空公司加入战局——长龙航空推出超低价国内随心飞产品！📅 预约时间：京东旅行已开启预约⏰ 开售时间：10月19日10:00 – 11月11日24:00打开京东App🔍搜索 长龙畅飞 ​_新浪新闻 — https://www.sina.cn/news/detail/5223775851514413.html (document: fetch_page-d08dfc467fb43c74)
98. 长龙航空2026夏航季新开多条航线 — https://zjnews.zjol.com.cn/yc/qmt/202603/t20260320_31562961.shtml (document: fetch_page-ef612d9eccb48c55)

## Claim Register

- (accepted, critical=true) 2026-08-15杭州到东莞共有8个高铁车次 [1]
- (accepted, critical=true) D3123次列车07:20从杭州东出发，18:00到达东莞南，历时10小时40分钟，二等座626元，一等座1001元 [1]
- (accepted, critical=true) D3123次列车07:20从杭州东出发，18:22到达东莞站，历时11时2分，二等座662元，一等座1043元 [1]
- (accepted, critical=false) G3023次列车10:13从杭州西出发 [1]
- (accepted, critical=false) G901次列车15:05从杭州西出发，20:51到达惠州北，二等座718元，一等座1149元，商务座2364元 [2]
- (accepted, critical=false) G2775次列车21:11从惠州北出发，21:27到达东莞南，二等座32元，一等座51元 [2]
- (accepted, critical=false) G3073次列车08:56从杭州西出发，14:59到达惠州北，二等座700元，一等座1119元 [2]
- (accepted, critical=false) G2735次列车15:37从惠州北出发，16:00到达东莞南，二等座32元，一等座51元 [2]
- (accepted, critical=false) D3123/D3122次列车07:20从杭州东站出发，18:22到达东莞站，经停27站，二等座704元，一等座1110元 [3]
- (accepted, critical=false) D3123/D3122次列车07:20从杭州东站出发，18:00到达东莞南站，历时10小时40分钟，经停26站，距离1434km，二等座668元，一等座1068元 [3]
- (accepted, critical=false) D913/D912次列车21:10从杭州东站出发，07:01到达东莞南站，历时9小时57分钟，经停2站，距离1499km，二等座668元，软卧上1061元，软卧下1194元 [3]
- (accepted, critical=false) D4913/D4912次列车21:10从杭州东站出发，07:01到达东莞南站，历时9小时57分钟，经停2站 [3]
- (accepted, critical=false) 由杭州开往东莞的高铁票价约为HK$227.48至HK$2,894.95 [4]
- (accepted, critical=false) 今天有8班高速列车从杭州开往东莞 [4]
- (accepted, critical=false) 由杭州开往东莞的首班高铁为07:20，末班车为21:10 [4]
- (accepted, critical=true) 12306官方购票渠道为铁路12306网站（kyfw.12306.cn）及12306手机APP，支持扫码登录购票。 [6]
- (accepted, critical=true) 铁路12306每日5:00至次日1:00（周二为5:00至24:00）提供购票、改签、变更到站业务办理，全天均可办理退票等其他服务。 [6]
- (accepted, critical=true) 在12306查询杭州西至东莞南的车次时，如果查询结果中没有满足需求的车次，可以使用中转换乘功能，查询途中换乘一次的列车余票情况。 [7]
- (accepted, critical=true) 12306显示的价格均为实际活动折扣后票价，具体票价以确认支付时实际购买的铺别票价为准。 [7]
- (accepted, critical=false) 12306提示，如因运力原因或其他不可控因素导致列车调度调整时，当前车型可能会发生变动。 [7]
- (accepted, critical=false) Trip.com提供由杭州前往东莞的高铁订票、时间表及票价查询服务。 [5]
- (accepted, critical=false) Trip.com提供由深圳北前往东莞的高铁订票、时间表及票价查询服务。 [5]
- (accepted, critical=false) 广州南站试行铁路出站换乘地铁'单向免检'，并启用一层南端便捷换乘区域等便民服务新举措，帮助旅客节省中转换乘时间。 [8]
- (accepted, critical=false) 购买了联程车票的旅客，到广州南站后可乘坐站台南端出站扶梯到达一楼南侧进行换乘。 [8]
- (accepted, critical=true) D913次列车21:10从杭州东出发，9时49分到达东莞南，二等座523元，动卧720元，无座523元 [9]
- (accepted, critical=false) D913次列车二等座523元，动卧720元，无座523元 [9]
- (accepted, critical=true) G3023次列车从杭州西出发，9时33分到达东莞南，二等座742.5元，一等座1210.5元，商务座2488元 [10]
- (accepted, critical=false) G3023次列车二等座742.5元，一等座1210.5元，商务座2488元，无座742.5元 [10]
- (accepted, critical=true) G901次列车15:05从杭州西出发，6时4分到达东莞南，二等座750元，一等座1200元，商务座2475元 [10]
- (accepted, critical=false) G901次列车二等座750元，一等座1200元，商务座2475元，无座750元 [10]
- (accepted, critical=false) D931次列车20:59从杭州东出发，9时45分到达虎门，二等座523元，动卧720元 [10]
- (accepted, critical=false) D931次列车二等座523元，动卧720元，无座523元 [10]
- (accepted, critical=true) 中转方案：14:12从杭州西出发，经惠州北换乘19分钟，全程6时31分到达东莞南 [9]
- (accepted, critical=false) G3087次列车14:12从杭州西出发，20:08到达惠州北，二等座701元，一等座1121元，商务座2304元 [9]
- (accepted, critical=false) G2747次列车20:27从惠州北出发，20:43到达东莞南，二等座32元，一等座51元，商务座111元 [9]
- (accepted, critical=false) 另一中转方案：15:05从杭州西出发，经惠州北换乘20分钟，全程6时22分到达东莞南 [9]
- (accepted, critical=false) T101次列车14:33从杭州南出发，16时9分到达东莞东，硬座195.5元，硬卧330.5元，软卧517.5元 [10,21]
- (accepted, critical=false) D21次列车14:40从杭州南出发，14时9分到达东莞东，二等座266元，二等卧432元，一等卧673元 [10]
- (accepted, critical=false) T211次列车从杭州南出发，次日05:27到达东莞东，硬座195.5元，硬卧354.5元，软卧540.5元 [11]
- (accepted, critical=false) 由杭州东开往东莞南的高铁票价约为HK$227.44至HK$2,894.44 [12]
- (accepted, critical=false) 今天有8班高速列车从杭州东开往东莞南 [12]
- (accepted, critical=false) 由杭州东开往东莞南的首班高铁为07:20，末班车为21:10 [12]
- (accepted, critical=false) 車票售罄時可先用 12306 候補，再比較前後班次、同城其他車站或中途轉乘。 [13]
- (accepted, critical=false) 不要為了上車刻意買錯乘車區間。 [13]
- (accepted, critical=false) 行程變動時，退票與改簽費用會受辦理時間、原車票與新車票條件影響。 [13]
- (accepted, critical=false) 台灣人可以用台胞證在 12306 買高鐵票。 [13]
- (accepted, critical=false) 2026 年台灣旅客搭大陸高鐵，最重要的只有三件事：用有效台胞證完成實名購票。 [13]
- (accepted, critical=false) 在 12306 網站首頁左上方的搜索框內，選擇購買的車票種類（單程或往返），選擇出發地和到達地以及出發日期，選擇是否只查詢高鐵或動車，完成後點擊「查詢」。 [14]
- (accepted, critical=false) 12306 查詢結果將顯示相關的車次、出發/到達時間、車程時間及車廂等級的剩餘座位資訊。 [14]
- (accepted, critical=false) 12306 網站會以人民幣票價發售車票。 [14]
- (accepted, critical=false) 12306 線上票務平台會以人民幣票價發售車票。 [15]
- (accepted, critical=false) 預售期第15天的車票發售時間因應出發站有所不同。 [15]
- (accepted, critical=false) 旅客可在12306手機App為發售第15天但未到開售時間的車票，預先選擇車次、車廂等級及乘車人，預填資料保留至開售後30分鐘。 [15]
- (accepted, critical=false) 使用居民身份證購票的，可憑購票時所使用的乘車人有效居民身份證原件到車站售票窗口、鐵路客票代售點或車站自動售票機上辦理換票。 [16]
- (accepted, critical=false) 有效身份證件信息、訂單號碼等不一致的，不能換票。 [16]
- (accepted, critical=true) 从杭州东到东莞有直达动车D3123，07:20从杭州东出发，10时40分到达东莞南，二等座626元，一等座1001元 [21]
- (accepted, critical=true) D3123次列车07:20从杭州东出发，11时2分到达东莞，二等座662元，一等座1043元 [21]
- (accepted, critical=true) G3023次高铁10:13从杭州西出发，9时33分到达东莞南，二等座742.5元，一等座1210.5元，商务座2488元 [21]
- (accepted, critical=true) G901次高铁15:05从杭州西出发，6时4分到达东莞南，二等座750元，一等座1200元，商务座2475元 [21]
- (accepted, critical=true) D931次动车20:59从杭州东出发，9时45分到达虎门，二等座523元，动卧720元 [21]
- (accepted, critical=true) D913次动车21:10从杭州东出发，9时49分到达东莞南，二等座515元，动卧740元，高级动卧1490元 [21]
- (accepted, critical=false) D21次动车14:40从杭州南出发，14时9分到达东莞东，二等座266元，二等卧432元，一等卧673元 [21]
- (accepted, critical=true) 中转方案：G3087次14:12从杭州西出发，20:08到达惠州北（二等座701元，一等座1121元），换乘停留19分后转G2747次20:27从惠州北出发，20:43到达东莞南（二等座32元，一等座51元），全程6时31分 [21]
- (accepted, critical=true) 中转方案：G901次15:05从杭州西出发，20:51到达惠州北（二等座718元），换乘停留20分后转G2775次21:11从惠州北出发，21:27到达东莞南（二等座32元，一等座51元），全程6时22分 [21]
- (accepted, critical=true) 中转方案：G3073次08:56从杭州西出发，14:59到达惠州北（二等座700元），换乘停留38分后转G2735次15:37从惠州北出发，16:00到达东莞南（二等座32元，一等座51元），全程7时4分 [21]
- (accepted, critical=true) 中转方案：G901次15:05从杭州西出发，21:09到达东莞南（二等座750元），换乘停留34分后转G6564次21:43从东莞南出发，22:06到达东莞（二等座47元，一等座59元），全程7时1分 [22]
- (accepted, critical=true) 中转方案：G1305次08:07从杭州西出发，13:45到达惠州北（二等座676元，一等座1081元），换乘停留1时52分后转G2735次15:37从惠州北出发，16:00到达东莞南（二等座32元，一等座51元），全程7时53分 [22]
- (accepted, critical=false) 2026-08-15当天杭州东到东莞共有8个车次 [21]
- (accepted, critical=true) 从杭州到广州的往返机票¥858起，单程机票¥399起 [28]
- (accepted, critical=false) 从杭州到广州已找到的最优惠航班为¥859 [28]
- (accepted, critical=false) 从杭州到广州票价最优惠的月份是九月 [28]
- (accepted, critical=true) 从杭州到广州的平均飞行时间为2小时19分钟 [28]
- (accepted, critical=false) 从杭州到广州最受欢迎的航空公司是四川航空 [28]
- (accepted, critical=false) 从杭州到广州每周平均航班数为413班 [28]
- (accepted, critical=true) 从杭州飞往广州约需2小时16分钟 [29]
- (accepted, critical=false) 从杭州萧山国际机场（HGH）飞往广州白云国际机场（CAN）的来回机票平均价格为UAH 17,053 [29]
- (accepted, critical=true) Air China、Shanghai Airlines、Sichuan Airlines、China Eastern Airlines、China Southern Airlines提供杭州飞广州的航班 [29]
- (accepted, critical=false) 提供杭州飞广州航班的航空公司还包括China Southern Airlines、China Eastern Airlines、Air China、Sichuan Airlines、Shanghai Airlines、Xiamen Airlines、9 Air、Hainan Airlines、Beijing Capital Airlines [29]
- (accepted, critical=false) 2026年9月3日杭州到广州的机票价格为RM 356 [27]
- (accepted, critical=false) ANA目前运行东京羽田、成田、大阪关西机场与北京、上海（虹桥/浦东）、广州、深圳、大连、青岛、杭州之间的往返航班 [30]
- (accepted, critical=true) 从东莞市到深圳宝安国际机场(SZX)的驾驶距离为36英里，开车大约需要52分钟。 [31]
- (accepted, critical=true) 从东莞市到深圳宝安国际机场(SZX)乘坐出租车约35.5英里，耗时52分钟，估计价格$26–32。 [31]
- (accepted, critical=false) 从东莞市到深圳宝安国际机场(SZX)的火车客运服务由Dongguan Rail Transit运营，到达Humen Station车站。 [31]
- (accepted, critical=true) 深圳机场汽车站到东莞万江的豪华大巴票价为￥45.00，发车时间从8:00开始，包括8:00、9:00、9:30、10:00、10:30、11:10、11:50、12:30、13:10、13:50等班次。 [32]
- (accepted, critical=true) 深圳宝安国际机场的城际大巴运营线包括香港、澳门、惠州、惠东、中山、东莞城市、东莞石龙、东莞大朗、东莞清溪、惠阳。 [33]
- (accepted, critical=false) 深圳宝安国际机场出租车夜间附加费为23:00至次日06:00，起步价升至13元且加收20%。 [33]
- (accepted, critical=false) 深圳宝安国际机场出租车等候费为0.8元/分钟，大件行李费为0.5元/件（体积＞0.2立方米、重量＞20千克）。 [33]
- (accepted, critical=false) 东莞城区到深圳宝安国际机场的大巴首车时间为7:20，末班时间为19:20。 [34]
- (accepted, critical=true) 从广州白云国际机场到东莞市的最便宜方式是线2地铁和火车，花费$5-$9，需要2小时19分钟。 [35]
- (accepted, critical=true) 从广州白云国际机场到东莞市的最快方式是开车，花费$10-$15，需要1小时1分钟。 [35]
- (accepted, critical=false) 从广州白云国际机场到东莞市没有直达巴士，但客运服务从Guangzhou Baiyun Airport出发，经过Dongguan Shilong到达Guangzhou Municipal，旅程（包括转乘）大约需要3小时15分钟。 [35]
- (accepted, critical=false) 从广州白云国际机场到东莞市没有直达火车，但客运服务从Guangzhou Airport South出发，经过Hongfu Road到达Guangzhou East和Guangdong。 [35]
- (accepted, critical=false) 广州白云机场到东莞的机场大巴部分班次预计车程为80分钟，发车时间包括00:50、07:40、08:10、08:50、09:30、10:00、10:40、11:20、12:00、12:40、13:20、13:50、14:30、15:00、15:40、16:20、17:00、17:40、18:20、19:00、19:50、20:40、21:30、22:30、23:30。 [36]
- (accepted, critical=false) 广州白云机场到东莞的机场大巴部分班次预计车程为120分钟，发车时间包括09:10、10:20、11:30、12:30、13:30、14:20、15:30、16:40、17:50、18:50、19:40、20:30。 [36]
- (accepted, critical=true) 白云机场空港快线大巴新增'东莞南城'线路，每天往返56个班次，约30分钟发一班车，单程行车时间约75分钟，票价52元。 [37]
- (accepted, critical=false) 白云机场往返东莞南城方向首班车为07:30，末班车为23:50。 [37]
- (accepted, critical=false) 东莞南城候机楼地址为东莞市东莞大道宏成五金城1号，电话0769-23151111。 [37]
- (accepted, critical=true) 2025年10月30日12时，广州白云国际机场T3航站楼正式启用，东方航空、上海航空、中国联合航空、吉祥航空、奥捷航空将首批入驻。 [38]
- (accepted, critical=true) 自西平西站出发，最快仅需57分钟即可抵达白云机场东站（T3）。 [38]
- (accepted, critical=false) 东莞全市共有12个城轨站点可直达白云机场。 [38]
- (accepted, critical=true) 杭州萧山机场有飞往深圳宝安的航班，航班号CZ3570，计划时间1130-1345，机型JET [39]
- (accepted, critical=true) 杭州萧山机场有飞往深圳宝安的航班，航班号HU7394，机型78A，计划时间1155-1425 [39]
- (accepted, critical=false) 杭州萧山机场有飞往深圳宝安的航班，航班号JET，计划时间1130-1345 [39]
- (accepted, critical=false) 深圳横岗长途汽车客运站有发往东莞的班次，发车时间包括7:45、9:10、10:00、11:30、13:00、14:10、15:40、16:20、18:05，票价均为55元，车型为大型高一座。 [41]
- (accepted, critical=false) 深圳横岗长途汽车客运站地址为深圳市龙岗区横岗镇深惠公路荷坳牛奶公司旁，联系电话28625268。 [41]
- (accepted, critical=false) 巴巴快巴提供汽车票网上订票服务，帮助热线为400-96520-88。 [42]
- (accepted, critical=false) 巴巴快巴平台提供杭州各大汽车站至浙江省内及上海、江苏省、安徽省等地的部分线路票价调整公告。 [42]
- (accepted, critical=true) 从杭州到东莞自驾总距离为1288.1公里 [44,55]
- (accepted, critical=true) 从杭州到东莞自驾总耗时为15.5小时 [44,55]
- (accepted, critical=true) 从杭州到东莞自驾油费为773元 [44,55]
- (accepted, critical=true) 从杭州到东莞自驾路桥费为630元 [44,55]
- (accepted, critical=true) 从杭州到东莞自驾总费用为1403元 [44,55]
- (accepted, critical=true) 从杭州到东莞自驾途经的高速包括杭新景高速、长深高速、龙丽温高速、沪昆高速、济广高速、厦蓉高速、赣州绕城高速、大广高速、龙河高速、珠三角环线高速等 [44]
- (accepted, critical=false) 沪昆高速（G60）起于上海市闵行区沪闵路立交，终点止于云南省昆明市盘龙区小庄立交，全长2353千米 [46]
- (accepted, critical=false) 沪昆高速（G60）途经浙江省的杭州市、嘉兴市、金华市、衢州市 [46]
- (accepted, critical=false) 沪昆高速是中国国家高速公路网18条东西横向干线的第13条 [46]
- (accepted, critical=false) 从杭州出发自驾上杭新景高速，该路段收费138公里 [45]
- (accepted, critical=false) 从杭州出发自驾上杭新龙高速，该路段收费32.7公里 [45]
- (accepted, critical=false) 从杭州出发自驾下杭金衢高速出口走杭金衢高速，该路段收费82.6公里 [45]
- (accepted, critical=false) 从杭州出发自驾在浙赣收费站处上沪昆高速，该路段收费18.0公里 [45]
- (accepted, critical=true) 杭州东到东莞有D3123/D3122次列车，07:20出发，18:22到达东莞站，经停27站，二等座¥704，一等座¥1110。 [3]
- (accepted, critical=true) 杭州东到东莞南有D3123/D3122次列车，历时10小时40分钟，经停26站，距离1434km，二等座¥668，一等座¥1068。 [3]
- (accepted, critical=true) 杭州东到东莞南有D913/D912次列车，21:10出发，07:01到达，历时9小时57分钟，经停2站，距离1499km，二等座¥668，软卧上¥1061，软卧下¥1194。 [3]
- (accepted, critical=true) 杭州西到东莞南有G3023次高铁，历时9小时33分钟，二等座¥742.5，一等座¥1210.5，商务座¥2488，无座¥742.5。 [10]
- (accepted, critical=true) 杭州南到东莞东有T101次列车，14:33出发，历时16小时9分，次日06:42到达，硬座¥195.5，硬卧¥330.5，软卧¥517.5，无座¥195.5。 [10]
- (accepted, critical=true) 杭州南到东莞东有D21次列车，14:40出发，历时14小时9分，次日04:49到达，二等座¥266，二等卧¥432，一等卧¥673，无座¥266。 [10]
- (accepted, critical=true) 杭州西到东莞南有G901次高铁，15:05出发，历时6小时4分，21:09到达，二等座¥750，一等座¥1200，商务座¥2475，无座¥750。 [10]
- (accepted, critical=true) 杭州东到虎门有D931次列车，20:59出发，历时9小时45分，次日06:44到达，二等座¥523，动卧¥720，无座¥523。 [10]
- (accepted, critical=false) 杭州去东莞高铁火车票价格低至HK$227.48。 [48]
- (accepted, critical=false) 杭州至东莞每日约有8个班次列车。 [48]
- (qualified, critical=false) 杭州东到东莞南有D4913/D4912次列车，21:10出发，07:01到达，历时9小时57分钟，经停2站。 [3]
- (accepted, critical=true) 杭州西到东莞南有G3023次高铁，10:13出发，历时9小时33分，19:46到达，二等座¥742.5，一等座¥1210.5，商务座¥2488，无座¥742.5。 [49]
- (accepted, critical=true) 杭州西到东莞南的高铁G3023次列车，9时33分，二等座票价742.5元，一等座1210.5元，商务座2488元 [50]
- (accepted, critical=true) 杭州南到东莞东的T101次列车，16时9分，硬座195.5元，硬卧330.5元，软卧517.5元 [50]
- (accepted, critical=true) 杭州南到东莞东的D21次列车，14时9分，二等座266元，二等卧432元，一等卧673元 [50]
- (accepted, critical=true) 杭州西到东莞南的高铁G901次列车，6时4分，二等座750元，一等座1200元，商务座2475元 [50]
- (accepted, critical=true) 杭州东到虎门的D931次列车，9时45分，二等座523元，动卧720元 [50]
- (accepted, critical=false) 深圳横岗长途汽车客运站到东莞的班次票价均为55元，车型为大型高一座 [53]
- (accepted, critical=false) 深圳横岗长途汽车客运站到东莞的发车时间包括7:45、9:10、10:00、11:30、13:00、14:10、15:40、16:20、18:05 [53]
- (accepted, critical=false) 深圳横岗长途汽车客运站地址为深圳市龙岗区横岗镇深惠公路荷坳牛奶公司旁，联系电话28625268 [53]
- (accepted, critical=true) 从杭州到东莞自驾途经的高速包括杭新景高速、长深高速、龙丽温高速、沪昆高速、济广高速、厦蓉高速、赣州绕城高速、大广高速、龙河高速、珠三角环线高速 [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过沪昆高速公路（G60） [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过长深高速公路（G25） [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过大广高速公路 [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过济广高速公路 [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过珠三角环线高速公路（G94） [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过龙河高速公路 [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过厦蓉高速公路 [55]
- (accepted, critical=true) 从杭州到东莞自驾路线经过赣州绕城高速公路 [55]
- (accepted, critical=false) 学生优惠票退票后返还优惠次数。 [60]
- (accepted, critical=true) 院校所在地需与学信网信息一致，家庭居住地可依实际变动修改，且不限修改次数。 [60]
- (accepted, critical=true) 动车组学生票按执行票价7.5折计算，最低可达公布票价4折。 [60]
- (accepted, critical=false) 普速列车学生票维持现行政策，硬座5折、硬卧加收硬卧与硬座全价差额。 [60]
- (accepted, critical=true) 铁路12306客户端学生预约购票服务实现常态化运行，开放时间从寒暑假期拓展至全年。 [60]
- (accepted, critical=false) 符合条件学生可在开车前20天至17天提报预约需求。 [60]
- (accepted, critical=false) 2026年春运期间，学生旅客可在开车前第20天5时至第17天23时提报预约需求，同一账户最多可同时提交3个订单，每个订单可提交同一乘车日期的5个"车次+席别"的组合。 [61]
- (accepted, critical=false) 在校学生最多可为包含本人在内的19名学生旅客预约。 [61]
- (accepted, critical=true) 学生每学年乘车前应在线完成学生优惠资质核验或到车站指定售票窗口或自动售票机办理一次本人居民身份证件与火车票学生优惠卡的优惠资质核验手续。 [62]
- (accepted, critical=true) 火车票学生优惠卡内需载明学生姓名、有效身份证件号码、优惠乘车区间、入学日期、优惠乘车次数等信息。 [62]
- (accepted, critical=true) 应有而没有"火车票学生优惠卡"，"火车票学生优惠卡"所载信息不全、不能识别或者与学生证记载不一致的，不发售学生优惠票。 [62]
- (accepted, critical=false) 在减价优惠区间内购买联程车票时，开车时间在5天以内的扣减1次优惠次数。 [62]
- (accepted, critical=false) 杭州东到东莞南站有G4899次列车，21:15发车，07:46到达，历时10小时37分钟，经停2站。 [68]
- (accepted, critical=false) 杭州东到东莞南站有列车，二等座票价¥783，特等/商务座¥1409，软卧上¥2127，软卧下¥2393。 [68]
- (accepted, critical=false) 杭州西站到东莞南站有3列列车，杭州东站到东莞南站有2列，杭州南站到东莞东站有2列，杭州东站到虎门站有1列。 [68]
- (accepted, critical=false) 杭州东到东莞站有D3123/D3122次列车，07:20发车，18:22到达，经停27站。 [68]
- (accepted, critical=false) 由杭州開往東莞的高鐵票價約爲 HK$227.48 至 HK$2,894.95，價格因列車類型、座位等級及路線而異。 [69]
- (accepted, critical=false) 今天有8班高速列車從杭州開往東莞。 [69]
- (accepted, critical=false) 由杭州開往東莞的首班高鐵為07:20，末班車為21:10。 [69]
- (accepted, critical=false) 除需通勤上學的學生，以及已獲鐵路公司同意照顧的情況外，14歲以下兒童搭乘由杭州至東莞的高鐵必須由成人陪同。 [69]
- (accepted, critical=false) 小童票適用於出行當日年滿6至13歲的乘客，年齡將以實際乘車日期計算。 [69]
- (accepted, critical=false) 杭州东到东莞南有D913次列车，21:10发车，历时9时49分，06:59+1到达，二等座¥515，动卧¥740，高级动卧¥1490，无座¥515。 [70]
- (accepted, critical=false) 2026-08-15出发的G3087次列车从杭州西14:12出发，20:08到达惠州北，二等座¥701，一等座¥1121，商务座¥2304，无座¥701。 [70]
- (accepted, critical=false) 2026-08-15出发的G2747次列车从惠州北20:27出发，20:43到达东莞南，二等座¥32，一等座¥51，商务座¥111，无座¥42。 [70]
- (accepted, critical=false) 12306购票系统在选择乘车人时，若当前选择的优先席别有不支持学生票的，会提示是否选择购买成人票。 [71]
- (accepted, critical=true) 学生旅客每学年（10月1日至次年9月30日）4次单程优惠票可随时使用 [72,79]
- (accepted, critical=true) 学生优惠区间可根据家庭居住地至学校所在地调整设置 [72]
- (accepted, critical=true) 动车组列车学生优惠票适用范围扩大至二等座、一等座和卧铺各席别 [72]
- (accepted, critical=true) 动车组列车学生优惠票票价调整为按执行票价7.5折计算 [72]
- (accepted, critical=true) 相关优惠车票预计将于9月6日开始发售 [72]
- (accepted, critical=true) 学生优惠票使用不再限于寒暑假期，可在每学年内随时使用 [72,79]
- (accepted, critical=false) 学生优惠票办理退票后将返还优惠次数 [72]
- (accepted, critical=true) 学生优惠票原适用区间为'家庭居住地至院校所在地'，优化调整后，院校所在地须与学信网信息一致 [72]
- (accepted, critical=true) 动车组列车学生优惠票计价规则由'公布票价的7.5折'调整为'执行票价的7.5折'，相当于'折上折'，最低折扣为公布票价4折 [73]
- (accepted, critical=false) 普速旅客列车学生优惠票按现行政策规定执行、保持不变，硬座按票价5折计算，硬卧加收硬卧与硬座的全价差额 [73]
- (accepted, critical=true) 铁路12306客户端学生预约购票功能开放时间由原来的寒暑期拓展至全年，实行常态化运行，符合条件的学生旅客可在开车前第20天至第17天提报预约需求 [73,79]
- (accepted, critical=true) 在校学生已通过优惠资质核验的，出行时铁路部门将不再查验学生证；未通过优惠资质核验的，仍需携带学生证乘车，铁路部门将依规查验学生证 [73]
- (accepted, critical=true) 入学新生可凭录取通知书线上、线下购买学生优惠票出行 [73]
- (accepted, critical=true) 计价规则优化后的学生优惠车票9月6日开始发售 [73]
- (accepted, critical=true) 学生旅客可通过铁路12306网站、客户端、微信等渠道查询 [73,79]
- (accepted, critical=true) 杭州至东莞有高铁车次，如G3023从杭州西到东莞南，二等座票价742.5元 [49]
- (accepted, critical=false) 杭州至东莞有普速列车T101从杭州南到东莞东，硬座票价195.5元 [49]
- (accepted, critical=false) 杭州至东莞有动车D21从杭州南到东莞东，二等座票价266元 [49]
- (accepted, critical=false) 杭州至东莞有高铁G901从杭州西到东莞南，二等座票价750元 [49]
- (accepted, critical=true) 学生优惠票办理退票后将返还优惠次数 [79]
- (accepted, critical=true) 优惠区间可根据家庭居住地至学校所在地调整设置，院校所在地须与学信网信息一致，家庭居住地可根据实际变动情况设置，修改次数不限 [79]
- (accepted, critical=true) 动车组列车学生优惠票适用席别范围由“仅限二等座”调整为“包括二等座、一等座和动车组卧铺各席别” [79]
- (accepted, critical=false) 普速旅客列车学生优惠票适用范围不变，仍为硬座、硬卧 [79]
- (accepted, critical=true) 动车组列车学生优惠票计价规则由“公布票价的7.5折”调整为“执行票价的7.5折”，相当于“折上折”，最低折扣为公布票价4折 [79]
- (accepted, critical=false) 普速旅客列车学生优惠票硬座按票价5折计算，硬卧加收硬卧与硬座的全价差额 [79]
- (accepted, critical=true) 在校学生已通过优惠资质核验的，出行时铁路部门将不再查验学生证；未通过优惠资质核验的，仍需携带学生证乘车 [79]
- (accepted, critical=false) 入学新生可凭录取通知书线上、线下购买学生优惠票出行 [79]
- (accepted, critical=false) 相关优惠车票9月6日开始发售 [79]
- (accepted, critical=true) 长龙航空365畅飞卡售价365元，下单后即可兑换经济舱M舱机票，不限次数，每次仅需再支付266元 [81]
- (accepted, critical=false) 长龙航空365畅飞卡PLUS版本售价2345元，除普通版本的兑换权益外，额外享经济舱其他舱位8折优惠 [81]
- (accepted, critical=true) 长龙航空365畅飞卡首次实现换票无时段限制、全天均可飞 [81]
- (accepted, critical=true) 长龙航空365畅飞卡一年时间内（2025年10月26日至2026年10月24日，特殊日期除外）都可兑换长龙航空国内自营航线 [81]
- (accepted, critical=true) 长龙航空总部在杭州，江浙沪地区航线密集，共有100多条航线辐射全国 [81,82,88,92]
- (accepted, critical=false) 长龙航空365畅飞卡于10月19日在京东旅行限时开售 [81]
- (accepted, critical=true) 长龙航空365畅飞卡可兑换长龙航空国内自营航线 [82]
- (accepted, critical=false) 长龙航空365畅飞卡售价365元，每次兑换仅需再支付266元 [82]
- (accepted, critical=false) 长龙航空365畅飞卡PLUS版本售价2345元 [82]
- (accepted, critical=false) 长龙航空365畅飞卡换票无时段限制、全天均可飞 [82]
- (accepted, critical=true) 长龙航空365畅飞卡有效期自2025年10月26日至2026年10月24日，特殊日期除外 [82]
- (qualified, critical=true) 长龙航空365畅飞卡国内部分卡目前无法使用 [80]
- (accepted, critical=false) 长龙航空有从广州到喀什的航线，经停郑州 [80]
- (accepted, critical=false) 长龙航空广州去乌鲁木齐没有航线，但有到喀什的航线 [80]
- (accepted, critical=false) 长龙航空7月1日起正式发售"长龙自由GO"旅行卡产品 [83]
- (accepted, critical=false) 长龙自由GO旅行卡支付现金4999元，即可额外获得1000元，卡内可用额度共计5999元 [83]
- (accepted, critical=false) 长龙自由GO旅行卡适用长龙航空所有国内自营航班 [83]
- (accepted, critical=true) 2022年夏航季长龙航空执飞国内航线130余条，通达北京、广州、成都、重庆、西安、丽江等国内城市近90余座 [83]
- (accepted, critical=false) 长龙自由GO旅行卡使用时间自由，节假日及出行高峰期均可以使用 [83]
- (accepted, critical=true) 长龙航空畅飞卡365元套餐提供全年无限次飞行，平均每天仅1元 [84]
- (accepted, critical=true) 畅飞卡覆盖全天航班，不用熬夜赶红眼航班 [84]
- (accepted, critical=true) 除特殊日期外，畅飞卡可兑换长龙航空国内自营航线，全年不限次数 [84]
- (accepted, critical=true) 长龙航空拥有73架客机、100+国内航线，覆盖杭州、宁波、温州、哈尔滨、长春、银川、广州、深圳、成都等城市 [84]
- (accepted, critical=true) 长龙航空航线覆盖广州和深圳，因此畅飞卡可用于杭州往返广州或深圳 [84]
- (accepted, critical=true) 长龙航空作为浙江省主基地航空公司，在新航季共执飞浙江省内进出港航线93条，其中国内航线84条，通达北京、广州、深圳、成都、西安、重庆、丽江等主要旅游城市 [85]
- (accepted, critical=true) 长龙航空推出畅飞卡系列、商旅卡等权益类产品，兼顾灵活性与性价比 [85]
- (accepted, critical=true) 长龙航空近期通航的城市包括重庆、西安、武汉、广州、深圳、成都等 [86]
- (accepted, critical=false) 长龙航空构建以杭州为中心的全国4小时交通圈 [86]
- (accepted, critical=false) 长龙航空畅飞卡365元套餐一年无限次飞行，性价比超高 [84]
- (accepted, critical=true) 长龙航空“365畅飞卡”售价365元，下单后即可兑换经济舱M舱机票，不限次数，每次仅需再支付266元 [88]
- (accepted, critical=true) 长龙航空“365畅飞卡”一年时间内（2025年10月26日至2026年10月24日，特殊日期除外）都可兑换长龙航空国内自营航线 [88]
- (accepted, critical=true) 长龙航空“365畅飞卡”首次实现换票无时段限制、全天均可飞 [88]
- (accepted, critical=false) “365畅飞卡PLUS”版本售价2345元，除普通版本的兑换权益外，额外享经济舱其他舱位8折优惠 [88]
- (accepted, critical=true) “365畅飞卡”系列产品兑换不受时段限制，一天24小时有航班就可约，全时段畅飞、全年不限次 [90]
- (accepted, critical=false) 京东旅行联合长龙航空推出“365畅飞卡”，价格仅365元，刷新行业纪录 [90]
- (accepted, critical=false) 长龙航空多次卡产品价格499元/899元/1299元（一套），不同航线对应不同价位组，产品价格均不含民航发展基金和燃油附加费 [89]
- (accepted, critical=false) 长龙航空多次卡产品权益为在适用范围内享受2次经济舱单程飞行权益 [89]
- (accepted, critical=false) 长龙航空多次卡产品适用航班为长龙航空指定国内自营航班，其中港澳台地区航班、包机以及代码共享航班除外 [89]
- (accepted, critical=true) 长龙航空随心飞产品分为“365畅飞卡”和“365畅飞卡PLUS”两个版本，前者售价365元，每次仅需再支付266元 [92]
- (accepted, critical=true) 365畅飞卡PLUS版本售价2345元，除普通版本的兑换权益外，额外享经济舱其他舱位8折优惠 [92]
- (accepted, critical=true) 365畅飞卡首次实现换票无时段限制、全天均可飞，一年时间内（2025年10月26日至2026年10月24日，特殊日期除外）都可兑换长龙航空国内自营航线 [92]
- (accepted, critical=true) 365畅飞卡售价仅365元，可兑换长龙航空所有时段航班，全时段畅飞、全年不限次 [92]
- (accepted, critical=false) 长龙航空最热门的机场是杭州 [95]
- (accepted, critical=false) 长龙航空目的地数量为83个 [95]
- (accepted, critical=true) 长龙航空推出“365畅飞卡”，售价365元，可兑换长龙航空所有时段航班，全时段畅飞、全年不限次。 [96]
- (accepted, critical=true) 长龙航空“365畅飞卡”在京东旅行限时销售，时间为10月19日10点至11月11日24点。 [96]
- (accepted, critical=true) 长龙航空随心飞产品分为“365畅飞卡”和“365畅飞卡PLUS”两个版本。 [96]
- (accepted, critical=true) 365畅飞卡售价365元，下单后即可兑换经济舱M舱机票，不限次数，每次仅需再支付266元。 [96]
- (accepted, critical=true) 365畅飞卡PLUS版本售价2345元，除普通版本的兑换权益外，额外享经济舱其他舱位8折优惠。 [96]
- (accepted, critical=true) 365畅飞卡一年时间内（2025年10月26日至2026年10月24日，特殊日期除外）都可兑换长龙航空国内自营航线。 [96]
- (accepted, critical=true) 365畅飞卡首次实现换票无时段限制、全天均可飞，拒绝“红眼航班”。 [96]
- (accepted, critical=false) 长龙航空总部在杭州，江浙沪地区航线密集，共有100多条航线辐射全国。 [96]
- (accepted, critical=true) 365元版本屏蔽了少数特殊航线（杭州=广州/哈尔滨/沈阳/长春/大连/贵阳）。 [97]
- (accepted, critical=false) 长龙航空拥有73架客机、100+国内航线，覆盖杭州、宁波、温州、哈尔滨、长春、银川、广州、深圳、成都等城市。 [97]
- (accepted, critical=false) 365畅飞卡PLUS售价2345元，包含365畅飞卡权益外加经济舱其他舱位8折购买现金票。 [97]
- (accepted, critical=true) 365畅飞卡每次换票需支付266元。 [97]
- (accepted, critical=false) 长龙航空2026年夏航季（3月29日起）预计执飞航线144条，其中国内航线125条，国际及地区航线19条。 [98]
- (accepted, critical=false) 长龙航空作为浙江省主基地航空公司，新航季共执飞浙江省内进出港航线93条，其中国内航线84条，通达北京、广州、深圳、成都、西安、重庆、丽江等主要旅游城市。 [98]
- (accepted, critical=false) 长龙航空推出畅飞卡系列、商旅卡等权益类产品。 [98]
