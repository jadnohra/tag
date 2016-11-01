libgen = require('libgen')


console.log('sadfsafd');
console.log(process.argv[2]);

var options = {
  mirror: 'http://libgen.io',
  query: process.argv[2],
  count: 1,
  sort_by: 'def', 
reverse: true
};

/*
libgen.latest.text('http://gen.lib.rus.ec',function(err,text){
  if (err) return console.error(err);
  console.log('Last text uploaded to Library Genesis');
  console.log('***********');
  console.log('Title: ' + text.title + Object.keys(text));
  console.log('Author: ' + text.author);
//  console.log('Download: ' +
  //            'http://gen.lib.rus.ec/book/index.php?md5=' +
    //          text.MD5.toLowerCase());
});
*/

libgen.search(options,function(err,data){
  if (err) { console.log('err'); return console.error(err); }
  var n = data.length;
  console.log(n + ' most recently published "' +
             options.query + '" books');
  while (n--){
    console.log('***********');
    console.log('Title: ' + data[n].title);
    console.log('Author: ' + data[n].author);
    //console.log('Download: ' +
    //            'http://gen.lib.rus.ec/book/index.php?md5=' +
    //            data[n].MD5.toLowerCase());
  }
});

console.log('end');
