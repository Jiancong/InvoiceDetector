
FONT_NAME="lancejie_shuipiao2"

echo Run Tesseract for Training.. 
tesseract $FONT_NAME.font.exp0.tif $FONT_NAME.font.exp0 nobatch box.train 
 
echo Compute the Character Set.. 
unicharset_extractor $FONT_NAME.font.exp0.box 
mftraining -F font_properties -U unicharset -O $FONT_NAME.unicharset $FONT_NAME.font.exp0.tr 


echo Clustering.. 
cntraining $FONT_NAME.font.exp0.tr 

echo Rename Files.. 
mv normproto $FONT_NAME.normproto 
mv inttemp $FONT_NAME.inttemp 
mv pffmtable $FONT_NAME.pffmtable 
mv shapetable $FONT_NAME.shapetable  

echo Create Tessdata.. 
combine_tessdata $FONT_NAME. 

