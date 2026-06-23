import html
import io
import json
import math
import re
import time
import zipfile
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone

from stocks.models import ScoreSnapshot, Stock


HTML_TAG_RE = re.compile(r"<[^>]+>")
PUNCT_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")


POSITIVE_KEYWORDS = {
    "수주",
    "계약",
    "공급",
    "흑자",
    "호실적",
    "최대 실적",
    "상회",
    "투자",
    "증설",
    "승인",
    "매수",
    "목표가 상향",
    "상향",
    "호조",
    "돌파",
    "신고가",
}
NEGATIVE_KEYWORDS = {
    "적자",
    "하회",
    "소송",
    "조사",
    "제재",
    "하락",
    "급락",
    "목표가 하향",
    "하향",
    "유상증자",
    "거래정지",
    "리콜",
    "불성실",
    "부진",
}


def normalize_disclosure_sentiment(title):
    if any(keyword in title for keyword in POSITIVE_KEYWORDS):
        return "positive"
    if any(keyword in title for keyword in NEGATIVE_KEYWORDS):
        return "negative"
    return "neutral"


class Command(BaseCommand):
    help = "네이버 뉴스와 선택적 OpenDART 데이터를 수집하고 AI로 종목별 뉴스 감성 점수를 갱신합니다."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="갱신할 종목코드 목록. 예: 005930 005930.KS")
        parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], help="시장 기준 갱신")
        parser.add_argument("--limit", type=int, default=20, help="갱신할 종목 수")
        parser.add_argument("--display", type=int, default=30, help="종목당 네이버 뉴스 요청 건수")
        parser.add_argument("--days", type=int, default=30, help="뉴스와 감성 점수에 반영할 최근 N일")
        parser.add_argument("--disclosure-days", type=int, default=365, help="화면에 저장할 공시 조회 기간")
        parser.add_argument("--ai-limit", type=int, default=10, help="종목당 AI로 정밀 분석할 최대 뉴스 수")
        parser.add_argument("--sleep", type=float, default=0.15, help="API 호출 사이 대기 시간")
        parser.add_argument("--include-dart", action="store_true", help="DART 공시 조회를 시도합니다.")
        parser.add_argument("--force", action="store_true", help="관련 뉴스가 없어도 기존 뉴스/공시 데이터를 비웁니다.")

    def handle(self, *args, **options):
        naver_enabled = bool(settings.NAVER_CLIENT_ID and settings.NAVER_CLIENT_SECRET)
        dart_enabled = bool(options["include_dart"] and settings.DART_API_KEY)
        if not naver_enabled and not dart_enabled:
            raise CommandError("뉴스는 NAVER_CLIENT_ID/NAVER_CLIENT_SECRET, 공시는 DART_API_KEY와 --include-dart가 필요합니다.")

        stocks = self.pick_stocks(options)
        if not stocks:
            self.stdout.write(self.style.WARNING("갱신할 종목이 없습니다."))
            return

        updated = 0
        for stock in stocks:
            score = ScoreSnapshot.objects.filter(stock=stock).order_by("-base_date").first()
            if not score:
                self.stdout.write(self.style.WARNING(f"{stock.ticker} {stock.name}: 점수 스냅샷 없음"))
                continue

            try:
                news = self.collect_naver_news(stock, options["display"], options["days"]) if naver_enabled else []
                news = self.dedupe(news)
                analyzed = [
                    self.analyze_article(stock, item, use_ai=index < options["ai_limit"])
                    for index, item in enumerate(news)
                ]
                analyzed = [item for item in analyzed if item["is_stock_relevant"] and item["relevance_score"] >= 0.45]
                disclosures = []
                if options["include_dart"]:
                    disclosure_rows = self.collect_dart_disclosures(stock, options["disclosure_days"])
                    disclosures = [self.analyze_article(stock, item, use_ai=False) for item in disclosure_rows]
                    disclosures = [
                        item for item in disclosures if item["is_stock_relevant"] and item["relevance_score"] >= 0.45
                    ]
            except requests.RequestException as exc:
                self.stdout.write(self.style.ERROR(f"{stock.ticker} {stock.name}: API 오류 - {exc}"))
                continue

            if analyzed or disclosures or options["force"]:
                scoring_disclosures = [item for item in disclosures if self.should_score_disclosure(item, options["days"])]
                aggregate = self.aggregate_sentiment([*analyzed, *scoring_disclosures])
                score.news = [self.serialize_article(item) for item in analyzed[:30]]
                score.disclosures = [self.serialize_article(item) for item in disclosures[:100]]
                
                if not isinstance(score.area_scores, dict):
                    score.area_scores = {}
                score.area_scores["newsSentiment"] = aggregate["score"]
                
                # Recalculate total_score incorporating news sentiment (10% weight)
                if aggregate["score"] is not None:
                    base_total = score.company_score * 0.45 + score.timing_score * 0.55
                    if base_total > 0:
                        discount_factor = score.total_score / base_total
                    else:
                        discount_factor = 1.0
                    new_base_total = base_total * 0.90 + aggregate["score"] * 0.10
                    score.total_score = max(0.0, min(100.0, round(new_base_total * discount_factor, 1)))
                
                score.scoring_log = self.replace_log_entry(score.scoring_log, aggregate)
                score.save(update_fields=["news", "disclosures", "area_scores", "total_score", "scoring_log"])
                updated += 1

            ns_display = f"{aggregate['score']:.1f}" if (aggregate["score"] is not None) else "None"
            self.stdout.write(
                f"{stock.ticker} {stock.name}: 뉴스 {len(analyzed)}건, 공시 {len(disclosures)}건, 감성 {ns_display}"
            )
            if options["sleep"] > 0:
                time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS(f"뉴스 감성 갱신 완료: {updated}/{len(stocks)}개 종목"))

    def pick_stocks(self, options):
        queryset = Stock.objects.filter(is_active=True).order_by("ticker")
        tickers = options.get("tickers") or []
        if tickers:
            normalized = set()
            for ticker in tickers:
                normalized.update(self.normalize_ticker_candidates(ticker))
            queryset = queryset.filter(ticker__in=normalized)
        elif options.get("market"):
            queryset = queryset.filter(market=options["market"])[: options["limit"]]
        else:
            base_date = ScoreSnapshot.objects.aggregate(value=Max("base_date"))["value"]
            tickers = (
                ScoreSnapshot.objects.filter(base_date=base_date)
                .order_by("-total_score")
                .values_list("stock_id", flat=True)[: options["limit"]]
            )
            queryset = queryset.filter(ticker__in=list(tickers))
        return list(queryset)

    def normalize_ticker_candidates(self, value):
        raw = str(value).strip().upper()
        if "." in raw:
            return [raw]
        code = raw.zfill(6)
        return [f"{code}.KS", f"{code}.KQ"]

    def collect_naver_news(self, stock, display, days):
        params = {
            "query": stock.name,
            "display": max(1, min(display, 100)),
            "start": 1,
            "sort": "date",
        }
        headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
        }
        response = requests.get(settings.NAVER_NEWS_URL, params=params, headers=headers, timeout=8)
        response.raise_for_status()
        cutoff = timezone.now() - timedelta(days=days)
        rows = []
        for item in response.json().get("items", []):
            published_at = self.parse_pub_date(item.get("pubDate"))
            if published_at and published_at < cutoff:
                continue
            title = self.clean_text(item.get("title", ""))
            summary = self.clean_text(item.get("description", ""))
            if not title:
                continue
            scope = self.news_scope(stock, title, summary)
            if scope == "direct" and not self.is_direct_news_title(stock, title):
                continue
            rows.append(
                {
                    "type": "뉴스",
                    "title": title,
                    "summary": summary,
                    "url": item.get("originallink") or item.get("link") or "",
                    "source": "",
                    "published_at": published_at,
                    "scope": scope,
                }
            )
        return rows

    def news_scope(self, stock, title, summary):
        text = f"{title} {summary}"
        market_terms = ["코스피", "코스닥", "증시", "지수", "환율", "금리", "연준", "리밸런싱", "서킷브레이커"]
        has_market = any(term and term in text for term in market_terms)
        title_has_market = any(term and term in title for term in market_terms)
        title_has_company = stock.name in title or stock.ticker.split(".")[0] in title
        if title_has_market and not title_has_company:
            return "market"
        has_company = stock.name in text or stock.ticker.split(".")[0] in text
        return "market" if has_market and not has_company else "direct"

    def is_direct_news_title(self, stock, title):
        terms = [
            stock.name,
            stock.ticker.split(".")[0],
            stock.sector,
            stock.primary_theme,
            "반도체",
            "HBM",
            "메모리",
            "파운드리",
            "갤럭시",
            "스마트폰",
            "AI",
            "실적",
            "영업이익",
            "매출",
            "목표가",
            "투자의견",
            "배당",
            "자사주",
            "공시",
            "투자",
            "증설",
            "수주",
            "공급",
        ]
        return any(term and term in title for term in terms)

    def collect_dart_disclosures(self, stock, days):
        if not settings.DART_API_KEY:
            return []
        corp_code = self.dart_corp_code(stock)
        if not corp_code:
            return []
        end = timezone.localdate()
        start = end - timedelta(days=days)
        response = requests.get(
            settings.DART_LIST_URL,
            params={
                "crtfc_key": settings.DART_API_KEY,
                "corp_code": corp_code,
                "bgn_de": start.strftime("%Y%m%d"),
                "end_de": end.strftime("%Y%m%d"),
                "last_reprt_at": "N",
                "sort": "date",
                "sort_mth": "desc",
                "page_no": 1,
                "page_count": 20,
            },
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"000", "013"}:
            self.stdout.write(self.style.WARNING(f"OpenDART 조회 실패: {stock.ticker} - {payload.get('message')}"))
            return []
        rows = []
        for item in payload.get("list", []):
            title = item.get("report_nm", "")
            category = self.disclosure_category(title, item.get("pblntf_ty", ""), item.get("pblntf_detail_ty", ""))
            rows.append(
                {
                    "type": "공시",
                    "title": title,
                    "summary": self.disclosure_summary(title, category, item),
                    "source": "OpenDART",
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
                    "published_at": self.dart_datetime(item.get("rcept_dt")),
                    "category": category,
                    "submitter": item.get("flr_nm", ""),
                    "is_correction": "정정" in title or "정정" in item.get("rm", ""),
                    "is_withdrawn": "철회" in title or "철회" in item.get("rm", ""),
                }
            )
        return rows

    def should_score_disclosure(self, item, days):
        important = {"실적", "배당", "증자·감자", "자기주식", "최대주주·지분", "계약·수주", "합병·분할", "사채 발행", "소송·규제"}
        if item.get("category") in important:
            return True
        published_at = item.get("published_at")
        if not published_at:
            return False
        return published_at >= timezone.now() - timedelta(days=days)


    def dart_corp_code(self, stock):
        mapping = self.load_dart_corp_mapping()
        return mapping.get(stock.ticker.split(".")[0])

    def load_dart_corp_mapping(self):
        cache_path = Path(settings.BASE_DIR) / ".cache" / "dart_corp_codes.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        response = requests.get(
            "https://opendart.fss.or.kr/api/corpCode.xml",
            params={"crtfc_key": settings.DART_API_KEY},
            timeout=15,
        )
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            xml_bytes = archive.read("CORPCODE.xml")
        root = ElementTree.fromstring(xml_bytes)
        mapping = {}
        for item in root.findall("list"):
            stock_code = (item.findtext("stock_code") or "").strip()
            corp_code = (item.findtext("corp_code") or "").strip()
            if stock_code and corp_code:
                mapping[stock_code] = corp_code
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        return mapping

    def dedupe(self, rows):
        kept = []
        fingerprints = []
        for row in rows:
            fingerprint = self.fingerprint(row["title"])
            if any(SequenceMatcher(None, fingerprint, previous).ratio() >= 0.84 for previous in fingerprints):
                continue
            kept.append(row)
            fingerprints.append(fingerprint)
        return kept

    def analyze_article(self, stock, article, use_ai=True):
        if use_ai and settings.GMS_API_KEY:
            analyzed = self.analyze_article_with_ai(stock, article)
            if analyzed:
                return {**article, **analyzed}
        return {**article, **self.analyze_article_locally(stock, article)}

    def analyze_article_with_ai(self, stock, article):
        prompt = {
            "stock": {"name": stock.name, "ticker": stock.ticker, "sector": stock.sector, "theme": stock.primary_theme},
            "article": {
                "title": article["title"],
                "summary": article["summary"],
                "source": article["source"],
                "published_at": article["published_at"].isoformat() if article["published_at"] else None,
            },
        }
        messages = [
            {
                "role": "developer",
                "content": (
                    "너는 한국 주식 뉴스 분석가다. 기사 제목과 요약만 보고 해당 종목 투자 판단에 필요한 "
                    "구조화 JSON만 반환한다. 본문을 보지 못하면 확인되지 않은 사실은 추정하지 않는다."
                ),
            },
            {
                "role": "user",
                "content": (
                    "다음 JSON 입력을 분석해서 JSON 객체만 반환해줘. "
                    "필드: relevance_score(0~1), is_stock_relevant(boolean), event_type, "
                    "sentiment(positive|neutral|negative), sentiment_score(-1~1), "
                    "impact(low|medium|high), impact_score(0~1), confidence(0~1), "
                    "time_horizon(short|medium|long), confirmed(boolean), reason, key_fact.\n"
                    f"{json.dumps(prompt, ensure_ascii=False)}"
                ),
            },
        ]
        try:
            response = requests.post(
                settings.GMS_CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {settings.GMS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GMS_CHAT_MODEL,
                    "messages": messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=settings.GMS_CHAT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return self.normalize_ai_result(data)
        except (KeyError, ValueError, requests.RequestException, json.JSONDecodeError) as exc:
            self.stdout.write(self.style.WARNING(f"AI 분석 실패, 키워드 분석으로 대체: {stock.ticker} - {exc}"))
            return None

    def analyze_article_locally(self, stock, article):
        text = f"{article['title']} {article['summary']}"
        name_hit = stock.name in text or stock.ticker.split(".")[0] in text
        theme_hit = bool((stock.sector and stock.sector in text) or (stock.primary_theme and stock.primary_theme in text))
        positive_hits = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
        negative_hits = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
        if positive_hits > negative_hits:
            sentiment = "positive"
            sentiment_score = min(0.85, 0.25 + positive_hits * 0.18)
        elif negative_hits > positive_hits:
            sentiment = "negative"
            sentiment_score = max(-0.85, -0.25 - negative_hits * 0.18)
        else:
            sentiment = "neutral"
            sentiment_score = 0
        is_relevant = article.get("type") == "공시" or name_hit or theme_hit or article.get("scope") == "market"
        relevance = 0.9 if name_hit or article.get("type") == "공시" else 0.65 if theme_hit or article.get("scope") == "market" else 0.2
        impact = "medium" if positive_hits + negative_hits else "low"
        impact_score = 0.65 if impact == "medium" else 0.35
        return {
            "relevance_score": relevance,
            "is_stock_relevant": is_relevant,
            "event_type": self.event_type(text),
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "impact": impact,
            "impact_score": impact_score,
            "confidence": 0.55 if positive_hits or negative_hits else 0.35,
            "time_horizon": "short",
            "confirmed": False,
            "reason": "기사 제목과 요약을 기준으로 분류했습니다.",
            "key_fact": article["title"][:90],
        }

    def normalize_ai_result(self, data):
        sentiment = str(data.get("sentiment") or "neutral").lower()
        if sentiment not in {"positive", "neutral", "negative"}:
            sentiment = "neutral"
        impact = str(data.get("impact") or "low").lower()
        if impact not in {"low", "medium", "high"}:
            impact = "low"
        return {
            "relevance_score": self.clamp_float(data.get("relevance_score"), 0, 1, 0.5),
            "is_stock_relevant": bool(data.get("is_stock_relevant", True)),
            "event_type": str(data.get("event_type") or "기타")[:40],
            "sentiment": sentiment,
            "sentiment_score": self.clamp_float(data.get("sentiment_score"), -1, 1, 0),
            "impact": impact,
            "impact_score": self.clamp_float(data.get("impact_score"), 0, 1, 0.4),
            "confidence": self.clamp_float(data.get("confidence"), 0, 1, 0.5),
            "time_horizon": str(data.get("time_horizon") or "short")[:20],
            "confirmed": bool(data.get("confirmed", False)),
            "reason": str(data.get("reason") or "AI 분석 결과입니다.")[:220],
            "key_fact": str(data.get("key_fact") or "")[:140],
        }

    def aggregate_sentiment(self, articles):
        if not articles:
            return {
                "type": "news_sentiment",
                "score": None,
                "label": "중립",
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "confidence": 0.0,
                "reason": "최근 수집된 종목 관련 뉴스가 없습니다.",
                "updated_at": timezone.now().isoformat(),
            }
        weighted_scores = []
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        now = timezone.now()
        for item in articles:
            counts[item["sentiment"]] += 1
            freshness = self.freshness_weight(item.get("published_at"), now)
            confirmation = 1.0 if item.get("confirmed") else 0.85
            source = 0.9
            scope = 0.35 if item.get("scope") == "market" else 1.0
            score = (
                item["sentiment_score"]
                * item["impact_score"]
                * item["relevance_score"]
                * item["confidence"]
                * freshness
                * source
                * scope
                * confirmation
            )
            weighted_scores.append(score)
            item["article_score"] = round(score, 4)
        raw = sum(weighted_scores)
        normalized = max(-1, min(1, raw))
        score_100 = round((normalized + 1) * 50, 1)
        confidence = round(sum(item["confidence"] for item in articles) / len(articles), 2)
        winner = max(counts, key=counts.get)
        return {
            "type": "news_sentiment",
            "score": score_100,
            "label": {"positive": "긍정", "neutral": "중립", "negative": "부정"}[winner],
            **counts,
            "confidence": confidence,
            "reason": f"최근 뉴스 {len(articles)}건을 분석해 긍정 {counts['positive']}건, 중립 {counts['neutral']}건, 부정 {counts['negative']}건으로 집계했습니다.",
            "updated_at": timezone.now().isoformat(),
        }

    def serialize_article(self, item):
        return {
            "type": item["type"],
            "title": item["title"],
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "publishedAt": item["published_at"].isoformat() if item.get("published_at") else None,
            "scope": item.get("scope", ""),
            "sentiment": item["sentiment"],
            "eventType": item.get("category") or item["event_type"],
            "category": item.get("category", ""),
            "submitter": item.get("submitter", ""),
            "isCorrection": item.get("is_correction", False),
            "isWithdrawn": item.get("is_withdrawn", False),
            "impact": item["impact"],
            "relevanceScore": item["relevance_score"],
            "sentimentScore": item["sentiment_score"],
            "impactScore": item["impact_score"],
            "confidence": item["confidence"],
            "articleScore": item.get("article_score", 0),
            "reason": item["reason"],
            "keyFact": item.get("key_fact", ""),
        }

    def replace_log_entry(self, log, aggregate):
        rows = [
            item
            for item in (log or [])
            if not (isinstance(item, dict) and item.get("type") == "news_sentiment")
        ]
        rows.append(aggregate)
        return rows

    def parse_pub_date(self, value):
        if not value:
            return None
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed, timezone=timezone.get_current_timezone())
        return parsed.astimezone(timezone.get_current_timezone())

    def dart_datetime(self, value):
        if not value or len(str(value)) != 8:
            return None
        text = str(value)
        parsed = datetime(int(text[:4]), int(text[4:6]), int(text[6:8]))
        return timezone.make_aware(parsed, timezone=timezone.get_current_timezone())

    def clean_text(self, value):
        return html.unescape(HTML_TAG_RE.sub("", str(value or ""))).strip()

    def fingerprint(self, value):
        return PUNCT_RE.sub("", value).lower()

    def event_type(self, text):
        if any(keyword in text for keyword in ["실적", "매출", "영업이익", "흑자", "적자"]):
            return "실적"
        if any(keyword in text for keyword in ["수주", "계약", "공급"]):
            return "수주·계약"
        if any(keyword in text for keyword in ["투자", "증설", "공장"]):
            return "투자·증설"
        if any(keyword in text for keyword in ["목표가", "매수", "투자의견"]):
            return "증권사 의견"
        if any(keyword in text for keyword in ["소송", "제재", "조사", "리콜"]):
            return "리스크"
        return "일반"

    def disclosure_category(self, title, notice_type="", detail_type=""):
        if notice_type == "I" or detail_type in {"I001", "I002", "I003"}:
            return "거래소 안내"
        if any(keyword in title for keyword in ["매출액", "영업이익", "잠정실적", "실적"]):
            return "실적"
        if any(keyword in title for keyword in ["배당", "현금ㆍ현물배당"]):
            return "배당"
        if any(keyword in title for keyword in ["유상증자", "무상증자", "감자"]):
            return "증자·감자"
        if any(keyword in title for keyword in ["자기주식"]):
            return "자기주식"
        if any(keyword in title for keyword in ["대량보유", "임원", "주요주주", "소유상황"]):
            return "최대주주·지분"
        if any(keyword in title for keyword in ["계약", "수주", "공급"]):
            return "계약·수주"
        if any(keyword in title for keyword in ["합병", "분할"]):
            return "합병·분할"
        if any(keyword in title for keyword in ["전환사채", "신주인수권", "사채"]):
            return "사채 발행"
        if any(keyword in title for keyword in ["소송", "제재", "횡령", "배임", "부도", "회생"]):
            return "소송·규제"
        return "기타"

    def disclosure_summary(self, title, category, item):
        submitter = item.get("flr_nm") or item.get("corp_name") or "제출인"
        if category == "거래소 안내":
            return f"{submitter}에서 접수한 시장 안내성 공시입니다. 회사 경영 악재와 구분해 확인하세요."
        if category == "기타":
            return f"{submitter}에서 접수한 공시입니다. 원문에서 세부 내용을 확인하세요."
        return f"{submitter}에서 접수한 {category} 관련 공시입니다."

    def freshness_weight(self, published_at, now):
        if not published_at:
            return 0.75
        hours = max(0.0, (now - published_at).total_seconds() / 3600)
        return max(0.35, math.exp(-hours / 96))

    def clamp_float(self, value, min_value, max_value, fallback):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(min_value, min(max_value, number))
