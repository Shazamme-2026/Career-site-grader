#!/bin/bash
# Runs full Lighthouse (all 4 categories, mobile default) on each URL in urls.txt.
# Writes per-site JSON to ./reports/ and appends a parsed summary row to results.csv.
DIR="/private/tmp/claude-501/-Users-rickmare-Code/7347f4fd-d2a1-46a7-a9fa-8bed88d085d5/scratchpad"
cd "$DIR" || exit 1
mkdir -p reports
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
echo "slug|provider|url|perf|access|bp|seo|fcp_s|lcp_s|tbt_ms|cls|si_s|status" > results.csv

while IFS='|' read -r slug provider url; do
  [ -z "$url" ] && continue
  out="reports/${slug}.json"
  echo ">>> $slug  $url"
  CHROME_PATH="$CHROME" npx --yes lighthouse "$url" \
    --quiet --output=json --output-path="$out" \
    --only-categories=performance,accessibility,best-practices,seo \
    --chrome-flags="--headless=new --no-sandbox --disable-gpu" \
    --max-wait-for-load=45000 \
    > "reports/${slug}.log" 2>&1
  if [ ! -s "$out" ]; then
    echo "${slug}|${provider}|${url}|||||||||FAILED" >> results.csv
    echo "    FAILED (see reports/${slug}.log)"
    continue
  fi
  node -e '
    const fs=require("fs");
    const [file,slug,provider,url]=process.argv.slice(1);
    try{
      const r=JSON.parse(fs.readFileSync(file,"utf8"));
      const c=r.categories||{};
      const a=r.audits||{};
      const pct=x=>x&&x.score!=null?Math.round(x.score*100):"";
      const perf=pct(c.performance),acc=pct(c["accessibility"]),bp=pct(c["best-practices"]),seo=pct(c.seo);
      const fcp=a["first-contentful-paint"]?.numericValue, lcp=a["largest-contentful-paint"]?.numericValue;
      const tbt=a["total-blocking-time"]?.numericValue, cls=a["cumulative-layout-shift"]?.numericValue, si=a["speed-index"]?.numericValue;
      const s=x=>x==null?"":(x/1000).toFixed(2);
      const row=[slug,provider,url,perf,acc,bp,seo,s(fcp),s(lcp),tbt==null?"":Math.round(tbt),cls==null?"":cls.toFixed(3),s(si),"OK"].join("|");
      fs.appendFileSync("results.csv",row+"\n");
      console.log("    perf="+perf+" a11y="+acc+" bp="+bp+" seo="+seo);
    }catch(e){
      fs.appendFileSync("results.csv",[slug,provider,url,"","","","","","","","","","PARSE_ERR"].join("|")+"\n");
      console.log("    PARSE_ERR "+e.message);
    }
  ' "$out" "$slug" "$provider" "$url"
done < urls.txt
echo "=== DONE ==="
