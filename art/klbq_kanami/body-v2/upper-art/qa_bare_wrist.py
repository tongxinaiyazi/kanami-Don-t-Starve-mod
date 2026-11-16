"""Selected integration poses with original hands; mixed native head/legs TEMP ONLY."""
from pathlib import Path
from PIL import Image,ImageDraw
ART=Path(__file__).resolve().parents[1]
p=ART/'hand-art/qa_hands.py';ctx={'__file__':str(p.resolve())}
# Reuse reference+registration loader only, not its full-cycle export side effects.
exec(p.read_text(encoding='utf8').split('tiles=[]')[0],ctx)
requests=[('player_idles','idle_loop',8,0,True),('player_idles','idle_loop',5,0,True),('player_idles','idle_loop',2,0,True),('player_basic','run_loop',8,8,True),('player_actions_eat','eat',255,8,False),('player_actions_axe','chop_loop',5,8,True)]
sheet=Image.new('RGB',(1320,960))
for n,(bank,name,face,index,carry) in enumerate(requests):
    anim=next(a for a in ctx['read_anim'](ctx['read_game_zip'](bank,'anim.bin')) if a['name']==name and a['facing']==face)
    im=ctx['render_frame'](anim['frames'][index],ctx['frames'],carry,True,size=(440,480),scale=1.5).convert('RGB')
    ImageDraw.Draw(im).text((4,4),f'{name}-{face}-{index}',fill='white')
    sheet.paste(im,((n%3)*440,(n//3)*480))
sheet.save('D:/SOFTWARE/CodexData/temp/kanami_upper_qa/bare-wrist-detail.png')
