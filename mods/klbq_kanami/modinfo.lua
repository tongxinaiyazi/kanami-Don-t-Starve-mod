name="香奈美 · 谢幕曲"
description="模组交流群：1131263408"
author="奈娅子"
version="2.4.0"
api_version=10
dst_compatible=true
dont_starve_compatible=false
reign_of_giants_compatible=false
client_only_mod=false
all_clients_require_mod=true
icon_atlas="modicon.xml"
icon="modicon.tex"
local keys={}
-- modinfo has a deliberately restricted environment, without string/ipairs.
local letters={"A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"}
for i=1,#letters do keys[i]={description=letters[i],data=i+96} end
configuration_options={
    {name="key_string",label="弦化按键",options=keys,default=114},
    {name="key_z",label="交响爆音按键",options=keys,default=122},
    {name="key_x",label="演出开始按键",options=keys,default=120},
    {name="key_requiem",label="镇魂歌圆斩按键",options=keys,default=118},
    {name="camera_distance",label="增幅镜头默认距离",options={{description="60",data=60},{description="80",data=80},{description="100",data=100}},default=80},
    {name="fate_crit_fraction",label="支配命运之轮暴击比例",hover="暴击按目标最大生命值计算，至少300真伤；暴击概率仍为10%。",options={{description="3%",data=.03},{description="5%",data=.05},{description="10%",data=.1},{description="20%",data=.2}},default=.03},
}
