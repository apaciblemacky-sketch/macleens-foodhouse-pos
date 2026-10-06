const http=require('http');
const {URL}=require('url');
const PORT=Number(process.env.PORT||10000), FLASK=5001, ULAM=5002;
function forward(req,res,target){
 const u=new URL(req.url,'http://127.0.0.1');
 const opts={hostname:'127.0.0.1',port:target,path:u.pathname+u.search,method:req.method,headers:{...req.headers,host:'127.0.0.1'}};
 const p=http.request(opts,r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});
 p.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end('Upstream unavailable')});req.pipe(p);
}
http.createServer((req,res)=>{
 if(req.url.startsWith('/ulam-voting')){req.url=req.url.replace(/^\/ulam-voting/,'')||'/';return forward(req,res,ULAM)}
 forward(req,res,FLASK);
}).listen(PORT,'0.0.0.0',()=>console.log('Maclean combined gateway on '+PORT));
