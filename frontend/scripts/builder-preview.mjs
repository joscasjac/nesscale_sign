// Fictional local preview only. Production rendering is server-side ReportLab.
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
export async function renderBuilder(data) {
 const doc=await PDFDocument.create();const normal=await doc.embedFont(StandardFonts.Helvetica),bold=await doc.embedFont(StandardFonts.HelveticaBold);
 for(const p of data.pages){const page=doc.addPage([595,842]);for(const b of p.blocks){const color=rgb(...(b.color||'#24362d').slice(1).match(/../g).map(h=>parseInt(h,16)/255));
 if(b.type==='Image'&&b.image){const image=b.image.startsWith('data:image/png')?await doc.embedPng(b.image):await doc.embedJpg(b.image);const fit=image.scaleToFit(b.width,b.height);page.drawImage(image,{x:b.x+(b.width-fit.width)/2,y:842-b.y-b.height+(b.height-fit.height)/2,...fit});continue;}
 if(b.type==='Divider'){page.drawLine({start:{x:b.x,y:842-b.y-b.height/2},end:{x:b.x+b.width,y:842-b.y-b.height/2},color});continue;}
 const font=b.type==='Heading'?bold:normal,size=b.font_size||12;let y=842-b.y-size;
 for(const line of String(b.text||'').replaceAll('\t','     ').split('\n')){let current='';for(const word of line.split(' ')){if(font.widthOfTextAtSize(current+word,size)>b.width&&current){page.drawText(current,{x:b.x,y,font,size,color});y-=size*1.35;current='';}current+=word+' ';}page.drawText(current,{x:b.x,y,font,size,color});y-=size*1.35;}
 }}return Buffer.from(await doc.save());
}
