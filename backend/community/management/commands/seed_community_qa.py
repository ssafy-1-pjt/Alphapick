from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from community.models import Comment, Post, PostLike
from stocks.models import Stock


PERSONAS = {
    "HBM할배": "hbm_halbae",
    "평단지킴이": "avg_guardian",
    "차트만봄": "chart_only",
    "공시줍줍": "filing_picker",
    "불나방88": "moth_88",
    "손절은예술": "stoploss_artist",
    "배당이월급": "dividend_salary",
    "오늘도추매": "buy_more_today",
    "국장졸업반": "kospi_senior",
    "mama": "mama",
    "산업덕후": "industry_nerd",
    "월급날매수": "payday_buyer",
    "하린버핏": "harin_buffett",
    "성익테리움": "seongik_eth",
    "민주풀악셀": "minju_fullaccel",
    "주현PLUS": "juhyun_plus",
}

AVATARS = {
    "HBM할배": {"kind": "chairman", "label": "HBM", "bg": ("#111827", "#64748b"), "fg": "#f8fafc"},
    "평단지킴이": {"kind": "guard", "label": "평단", "bg": ("#0f766e", "#ccfbf1"), "fg": "#062f2f"},
    "차트만봄": {"kind": "chart", "label": "차트", "bg": ("#020617", "#38bdf8"), "fg": "#f8fafc"},
    "공시줍줍": {"kind": "document", "label": "공시", "bg": ("#1d4ed8", "#dbeafe"), "fg": "#0f172a"},
    "불나방88": {"kind": "moth", "label": "88", "bg": ("#450a0a", "#fb923c"), "fg": "#fff7ed"},
    "손절은예술": {"kind": "scissors", "label": "손절", "bg": ("#4c1d95", "#c4b5fd"), "fg": "#f5f3ff"},
    "배당이월급": {"kind": "dividend", "label": "배당", "bg": ("#064e3b", "#facc15"), "fg": "#052e16"},
    "오늘도추매": {"kind": "shopping", "label": "추매", "bg": ("#14532d", "#86efac"), "fg": "#052e16"},
    "국장졸업반": {"kind": "gungye", "label": "국장", "bg": ("#312e81", "#fef3c7"), "fg": "#1e1b4b"},
    "mama": {"kind": "minimal", "label": ".", "bg": ("#be185d", "#fbcfe8"), "fg": "#500724"},
    "산업덕후": {"kind": "factory", "label": "산업", "bg": ("#854d0e", "#fde68a"), "fg": "#451a03"},
    "월급날매수": {"kind": "salaryman", "label": "월급", "bg": ("#0e7490", "#a5f3fc"), "fg": "#083344"},
    "하린버핏": {"kind": "chairman", "label": "존버", "bg": ("#0f172a", "#22c55e"), "fg": "#f8fafc"},
    "성익테리움": {"kind": "crypto", "label": "ETH", "bg": ("#1e1b4b", "#a78bfa"), "fg": "#f5f3ff"},
    "민주풀악셀": {"kind": "rocket", "label": "풀악셀", "bg": ("#7f1d1d", "#f97316"), "fg": "#fff7ed"},
    "주현PLUS": {"kind": "plus", "label": "PLUS", "bg": ("#581c87", "#f0abfc"), "fg": "#faf5ff"},
}


POSTS = [
    {
        "stock": ("000660.KS", "SK하이닉스"),
        "title": "아니 내가 사니까 바로 멈추네",
        "author": "불나방88",
        "content": "오늘 아침에 고민하다가 들어왔는데\n제가 매수한 가격이 오늘 고점이었습니다.\n\n이 정도면 증권사에서 인간 지표로 고용해야 하는 거 아닌가요?",
        "likes": 14,
        "comments": [
            ("차트만봄", "장 초반 거래량 터지고 윗꼬리 나온 거라 오늘 종가까지 봐야 합니다.\n바로 망했다고 결론 내리기엔 아직 이름.", [
                ("불나방88", "그 종가를 볼 심장이 없습니다."),
                ("손절은예술", "진입 전에 손절 기준부터 정했으면 심장이 조금 편했을 겁니다."),
            ]),
            ("HBM할배", "하이닉스는 하루 캔들보다 메모리 가격과 HBM 공급 흐름을 보는 종목입니다.\n다만 좋은 회사와 좋은 매수 가격은 다른 문제죠.", [
                ("평단지킴이", "좋은 회사인 건 알겠는데 제 계좌에는 왜 나쁘게 행동하나요."),
            ]),
            ("mama", "하닉아\n니가 먼저 꼬셨잖아", []),
            ("국장졸업반", "반도체 슈퍼사이클보다 빠른 게 개미 계좌 마이너스 전환입니다.", []),
        ],
    },
    {
        "stock": ("005930.KS", "삼성전자"),
        "title": "삼성전자 주주 특징",
        "author": "평단지킴이",
        "content": "휴대폰 삼성\nTV 삼성\n냉장고 삼성\n주식도 삼성\n\n그런데 수익만 타사 제품임.",
        "likes": 31,
        "comments": [
            ("월급날매수", "저는 매달 한 주씩만 사고 있습니다.\n많이 오르면 한 주, 많이 내려도 한 주라 마음은 편합니다.", [
                ("국장졸업반", "삼전이 횡보하는 동안 월급이 먼저 상승할 수도 있습니다."),
            ]),
            ("HBM할배", "삼성전자는 반도체만 보는 기업이 아니라서 회복 속도가 느리게 체감될 수 있습니다.\n파운드리, 메모리, 모바일이 동시에 좋아지는지가 중요합니다.", [
                ("평단지킴이", "제 평단도 동시에 좋아졌으면 좋겠습니다."),
            ]),
            ("mama", "전자제품 AS는 잘해주는데\n주주 계좌 AS는 어디에 신청하나요", []),
            ("차트만봄", "횡보가 길수록 방향이 나온 뒤에 따라가는 게 낫습니다.\n미리 지쳐서 던지는 사람이 많아지는 구간이긴 합니다.", [
                ("불나방88", "그럼 제가 던지면 출발한다는 뜻인가요?"),
                ("차트만봄", "통계적으로 본인 매매 기록부터 확인해보셔야 합니다."),
            ]),
        ],
    },
    {
        "stock": ("005380.KS", "현대차"),
        "title": "차는 잘 달리는데 주가는 왜 주차 중인가요",
        "author": "월급날매수",
        "content": "도로에서 현대차는 계속 보이는데\n제 계좌에 있는 현대차는 몇 주째 주차 브레이크 채워둔 느낌입니다.\n\n출차 예정 시간 아시는 분?",
        "likes": 22,
        "comments": [
            ("산업덕후", "자동차주는 판매량만큼 환율, 인센티브, 재고, 관세 우려에 민감합니다.\n차가 많이 보인다는 것과 이익이 늘어난다는 건 조금 다른 이야기입니다.", [
                ("mama", "차는 도로에\n주가는 지하주차장에"),
            ]),
            ("배당이월급", "현대차는 급등 기대보다는 실적과 주주환원을 같이 보는 편이 마음 편합니다.", [
                ("불나방88", "저는 마음이 편하려고 주식을 시작한 게 아닌가 봅니다."),
            ]),
            ("손절은예술", "횡보 종목에서 급하게 수익 내려고 비중을 늘리면 사람이 먼저 지칩니다.", []),
            ("국장졸업반", "출차하려면 주차요금부터 내셔야 합니다.\n주차요금은 보통 시간입니다.", []),
        ],
    },
    {
        "stock": ("012450.KS", "한화에어로스페이스"),
        "title": "로켓은 올라가는데 저는 왜 못 탔죠",
        "author": "불나방88",
        "content": "오를 때는 무서워서 못 사고\n조정 오면 더 떨어질까 봐 못 사고\n\n결국 뉴스만 누구보다 열심히 읽는 무주주입니다.",
        "likes": 42,
        "comments": [
            ("산업덕후", "방산주는 수주 뉴스가 바로 매출로 잡히는 게 아니라 계약과 인도 일정을 봐야 합니다.\n주가가 먼저 움직인 구간에서는 수주잔고와 밸류에이션을 같이 확인해야 합니다.", [
                ("불나방88", "설명은 이해했는데 매수 버튼은 더 어려워졌습니다."),
            ]),
            ("손절은예술", "못 산 것도 포지션입니다.\n놓쳤다고 생각해서 추격하는 순간 계획이 아니라 감정 매매가 됩니다.", [
                ("mama", "무주주도 포지션\n수익률 0% 방어 성공"),
            ]),
            ("국장졸업반", "로켓 발사할 때 탑승하는 건 우주비행사고\n개미는 보통 발사대 근처에서 표를 삽니다.", []),
            ("차트만봄", "거래량 동반 돌파 후 첫 눌림인지, 추세 이탈인지 구분해야 합니다.\n양봉만 보고 따라가는 건 위험합니다.", [
                ("평단지킴이", "저는 양봉을 보고 샀는데 음봉과 장기연애 중입니다."),
            ]),
        ],
    },
    {
        "stock": ("035420.KS", "NAVER"),
        "title": "네이버에 ‘내 주식 언제 오름’ 검색해봤습니다",
        "author": "mama",
        "content": "검색 결과가 없습니다.",
        "likes": 55,
        "comments": [
            ("국장졸업반", "연관 검색어:\n네이버 주주 탈출 방법\n네이버 평단 낮추는 법\n시간을 되돌리는 법", []),
            ("공시줍줍", "광고, 커머스, 핀테크, 콘텐츠, AI 비용을 따로 봐야 합니다.\n매출 성장보다 수익성이 회복되는지가 핵심입니다.", [
                ("mama", "저는 수익성이 아니라 수익률이 회복됐으면 합니다."),
            ]),
            ("월급날매수", "오래 들고 있으니 이제 포털 사이트가 아니라 고향 같습니다.", [
                ("평단지킴이", "고향은 돌아갈 수라도 있죠. 제 평단은 길이 끊겼습니다."),
            ]),
            ("불나방88", "오늘 양봉인데 이제 진짜 시작인가요?", [
                ("차트만봄", "NAVER 토론방에서 “이제 시작”이라는 글이 늘어나면 일단 거래량부터 확인합니다."),
            ]),
        ],
    },
    {
        "stock": ("105560.KS", "KB금융"),
        "title": "재미는 없는데 계좌는 제일 얌전함",
        "author": "배당이월급",
        "content": "반도체 보면서 심장 뛰고\n방산 보면서 배 아프고\n바이오 보면서 정신 잃다가\n\nKB금융 보면 다시 혈압이 정상으로 돌아옵니다.",
        "likes": 37,
        "comments": [
            ("월급날매수", "월급날마다 조금씩 모으기에는 이런 종목이 마음 편하긴 합니다.", []),
            ("불나방88", "그런데 하루에 10%씩 안 오르면 너무 심심하지 않나요?", [
                ("배당이월급", "하루에 10%씩 움직이는 종목을 들고 있으면 회사 업무가 심심해집니다."),
            ]),
            ("공시줍줍", "금융주는 순이자마진만 보지 말고 충당금, 자사주, 배당 정책까지 같이 봐야 합니다.", [
                ("국장졸업반", "이 방은 댓글에서도 금융교육을 해주시네요."),
            ]),
            ("mama", "배당 들어오는 날\n은행에서 용돈 받은 기분", []),
        ],
    },
    {
        "stock": ("005490.KS", "POSCO홀딩스"),
        "title": "이 회사 정체가 정확히 뭔가요",
        "author": "평단지킴이",
        "content": "철강주라고 해서 샀는데 2차전지라고 하고\n2차전지 보고 기다렸더니 다시 철강 이야기가 나오고\n\n제 계좌만 일관되게 철로 만들어졌습니다.",
        "likes": 46,
        "comments": [
            ("산업덕후", "철강 본업의 현금흐름과 신사업 투자 부담을 같이 보는 게 맞습니다.\n리튬 가격 하나만으로 전체 기업가치를 설명하면 빠지는 부분이 많습니다.", [
                ("평단지킴이", "기업은 다각화됐는데 제 손실은 한 방향입니다."),
            ]),
            ("오늘도추매", "오늘도 한 주 담았습니다.\n이제 가족보다 자주 만나는 종목입니다.", [
                ("손절은예술", "추가 매수 전에 최초 투자 논리가 아직 유효한지부터 확인하세요."),
                ("오늘도추매", "최초 투자 논리는 기억이 안 나고 평단만 기억납니다."),
            ]),
            ("국장졸업반", "철은 뜨거울 때 두드리라고 했는데\n저는 뜨거울 때 매수했습니다.", []),
            ("mama", "포스코\n나랑 포옹하고\n같이 울자", []),
        ],
    },
    {
        "stock": ("207940.KS", "삼성바이오로직스"),
        "title": "주가에도 바이오리듬이 있나요",
        "author": "월급날매수",
        "content": "오르는 날에는 너무 비싸 보여서 못 사고\n내리는 날에는 무서워서 못 사고\n\n매일 관찰만 하는데 이제 제가 주주인지 연구원인지 모르겠습니다.",
        "likes": 19,
        "comments": [
            ("공시줍줍", "바이오주는 단순 PER보다 수주, 공장 가동률, 증설 일정과 고객사 구성을 봐야 합니다.", [
                ("mama", "저는 가동률보다 제 계좌 회복률이 궁금합니다."),
            ]),
            ("불나방88", "오늘 장대양봉인데 지금 들어가도 되나요?", [
                ("손절은예술", "그 질문이 나올 때는 이미 본인이 추격 중인지부터 확인해야 합니다."),
            ]),
            ("국장졸업반", "바이오는 미래를 반영한다는데\n제 계좌는 과거의 실수를 계속 반영 중입니다.", []),
            ("차트만봄", "대형주라도 변동성이 커질 때는 한 번에 들어가기보다 기준을 나눠두는 편이 낫습니다.", []),
        ],
    },
    {
        "stock": ("373220.KS", "LG에너지솔루션"),
        "title": "배터리는 충전되는데 주주 체력은 방전됨",
        "author": "평단지킴이",
        "content": "완충까지 예상 시간\n알 수 없음",
        "likes": 63,
        "comments": [
            ("산업덕후", "전기차 판매량뿐 아니라 배터리 가격, 가동률, 고객사 재고 조정을 같이 봐야 합니다.\n업황이 회복돼도 실적 반영까지 시차가 생길 수 있습니다.", [
                ("평단지킴이", "제 체력에는 시차 없이 반영되고 있습니다."),
            ]),
            ("오늘도추매", "조금 더 담았습니다.\n이제 충전기가 아니라 발전소가 필요합니다.", [
                ("손절은예술", "계속 매수하는 것과 계획적으로 분할매수하는 건 다릅니다."),
            ]),
            ("mama", "배터리 잔량 1%\n주주 멘탈 잔량 0%", []),
            ("국장졸업반", "급속 충전 지원 종목인 줄 알았는데 저속 충전도 연결이 안 됩니다.", []),
        ],
    },
    {
        "stock": ("000660.KS", "SK하이닉스"),
        "title": "하이닉스 오늘 조정은 별로 걱정 안 됨",
        "author": "하린버핏",
        "content": "HBM 수요가 갑자기 사라진 것도 아니고\n장기적으로 보면 그냥 흔들리는 구간 같음.\n\n나는 조금 더 보유할 생각.",
        "likes": 3,
        "comments": [
            ("민주풀악셀", "“별로 걱정 안 됨”이라고 말하는 사람 특징\n아침 9시부터 호가창 보고 있음", [
                ("하린버핏", "나는 호가창 본 게 아니라 알림이 와서 본 거야."),
                ("민주풀악셀", "알림을 1% 단위로 설정해놨잖아."),
            ]),
            ("성익테리움", "그 돈이면 이더 샀으면 주말에도 움직였다.", [
                ("하린버핏", "주말에도 떨어지잖아."),
                ("성익테리움", "그건 24시간 매수 기회를 주는 거지."),
                ("주현PLUS", "그 논리면 YG PLUS도 매일 매수 기회를 줌."),
                ("성익테리움", "너는 기회가 몇 년째냐."),
            ]),
            ("주현PLUS", "하이닉스 한 주 가격이면 YG PLUS 여러 주 산다.", [
                ("하린버핏", "주식은 개수가 아니라 금액으로 사는 거야."),
                ("주현PLUS", "그래도 숫자가 많으면 든든해."),
            ]),
        ],
    },
    {
        "stock": ("005930.KS", "삼성전자"),
        "title": "삼성전자 다시 한 주 추가",
        "author": "하린버핏",
        "content": "단기적으로 답답한 건 맞는데\n이 가격에서 굳이 던질 이유도 없다고 생각함.",
        "likes": 2,
        "comments": [
            ("성익테리움", "삼성전자 한 주 살 돈이면 이더리움 0.0몇 개 가능.", [
                ("하린버핏", "그래서 그 0.0몇 개가 지금 얼마인데?"),
                ("성익테리움", "수량으로 투자 가치를 판단하면 안 되지."),
                ("하린버핏", "먼저 수량 이야기한 사람이 너야."),
            ]),
            ("민주풀악셀", "삼전은 너무 느려.\n내가 그동안 종목을 몇 번 갈아탔는데.", [
                ("하린버핏", "그래서 수익 났어?"),
                ("민주풀악셀", "종목 경험이 쌓였지."),
                ("주현PLUS", "나도 YG PLUS 경험만큼은 국내 1위야."),
            ]),
            ("주현PLUS", "삼성도 엔터 사업 하면 오를 것 같은데.", [
                ("민주풀악셀", "삼성전자 주주들이 단체로 화낼 소리 하지 마."),
            ]),
        ],
    },
    {
        "stock": ("005380.KS", "현대차"),
        "title": "현대차는 생각보다 저평가 같은데",
        "author": "하린버핏",
        "content": "실적이 크게 무너지지 않는다면\n주주환원까지 보고 천천히 모아갈 만해 보임.\n\n아직 매수는 안 했음.",
        "likes": 1,
        "comments": [
            ("민주풀악셀", "“아직 매수는 안 했음”\n하린이 기준 최고 수준의 부정적 평가.", [
                ("하린버핏", "가격을 더 보고 있다는 뜻이야."),
                ("민주풀악셀", "그렇게 보다가 20% 오르면 비싸다고 안 살 거잖아."),
            ]),
            ("성익테리움", "현대차를 왜 사냐.\n차 살 돈도 이더 사고 걸어 다니면 됨.", [
                ("주현PLUS", "너는 이더 떨어지면 걸을 힘도 없잖아."),
                ("성익테리움", "변동성을 견디는 것도 체력이다."),
            ]),
            ("주현PLUS", "현대차에 YG 아티스트 광고 모델 쓰면 호재임?", [
                ("민주풀악셀", "넌 종목 분석이 아니라 연결고리 찾기 게임을 하고 있어."),
            ]),
        ],
    },
    {
        "stock": ("012450.KS", "한화에어로스페이스"),
        "title": "조정 한 번만 더 주면 들어간다",
        "author": "민주풀악셀",
        "content": "수주잔고 있고 방산 사이클 살아 있고\n지금은 가격이 조금 부담스러워서 기다리는 중.\n\n딱 한 번만 눌려줘라.",
        "likes": 4,
        "comments": [
            ("하린버핏", "아까 이미 샀다고 하지 않았어?", [
                ("민주풀악셀", "일부만 샀고 본매수는 아직이야."),
                ("하린버핏", "그럼 들어간 거잖아."),
                ("민주풀악셀", "정찰병은 매수로 안 쳐."),
            ]),
            ("성익테리움", "방산주 살 돈이면 디지털 자산을 사야지.\n전쟁 없는 세상이 오면 방산은 끝이다.", [
                ("민주풀악셀", "인터넷 끊기면 이더는 어떻게 할 건데?"),
                ("성익테리움", "그런 극단적인 가정을 왜 해."),
                ("하린버핏", "전쟁 없는 세상은 극단적인 가정 아니고?"),
            ]),
            ("주현PLUS", "한화에서 YG 인수하면 둘 다 오르나?", [
                ("민주풀악셀", "한화 주주들이 먼저 매도할 듯."),
                ("주현PLUS", "새로운 성장 동력인데 왜?"),
            ]),
        ],
    },
    {
        "stock": ("066570.KS", "LG전자"),
        "title": "다들 가전회사로만 보는데 나는 다르게 봄",
        "author": "민주풀악셀",
        "content": "전장, 냉난방공조, 데이터센터 냉각까지 보면\n그냥 냉장고 회사는 아니라고 봄.\n\n시장이 아직 제대로 평가 안 하는 듯.",
        "likes": 3,
        "comments": [
            ("하린버핏", "사업 방향은 괜찮은데\n네가 매수한 이유는 어제 거래량 터져서잖아.", [
                ("민주풀악셀", "거래량으로 발견하고 사업을 공부한 거지."),
                ("하린버핏", "순서가 반대인 것 같은데."),
                ("민주풀악셀", "결과적으로 공부했으면 된 거야."),
            ]),
            ("성익테리움", "냉장고는 중앙화되어 있음.", [
                ("민주풀악셀", "냉장고가 왜 중앙화되어 있는데?"),
                ("성익테리움", "제조사가 통제하잖아."),
                ("하린버핏", "냉장고 문은 네가 열잖아."),
            ]),
            ("주현PLUS", "LG전자 오르면 YG PLUS도 같이 오를 가능성 있음?", [
                ("민주풀악셀", "없어."),
                ("주현PLUS", "시장은 항상 예상 밖으로 움직임."),
            ]),
        ],
    },
    {
        "stock": ("079550.KS", "LIG넥스원"),
        "title": "방산은 하루 빠졌다고 끝난 게 아님",
        "author": "민주풀악셀",
        "content": "수출 계약 하나만 추가로 나와도 분위기 바뀐다.\n나는 이런 날이 오히려 기회라고 봄.",
        "likes": 2,
        "comments": [
            ("하린버핏", "한화에어로도 샀고 LIG넥스원도 샀으면\n그냥 방산 ETF를 사는 게 낫지 않아?", [
                ("민주풀악셀", "종목마다 움직이는 타이밍이 달라."),
                ("하린버핏", "같이 빠지고 있는데?"),
                ("민주풀악셀", "오늘만 보면 그렇지."),
            ]),
            ("성익테리움", "내가 보기에는 민주 포트폴리오가 이더보다 변동성 큼.", [
                ("민주풀악셀", "이더 투자자가 변동성을 지적하네."),
                ("성익테리움", "나는 변동성을 알고 들어간 거고\n너는 우량주라고 믿고 들어간 거잖아."),
            ]),
            ("주현PLUS", "미사일 이름에 PLUS 붙이면 관심 가져봄.", [
                ("하린버핏", "넌 종목명을 보고 투자하는 거야?"),
                ("주현PLUS", "YG PLUS도 이름이 좋아서 처음 봤어."),
            ]),
        ],
    },
    {
        "stock": ("001510.KS", "SK증권"),
        "title": "여기 거래량 들어오는 거 나만 보임?",
        "author": "민주풀악셀",
        "content": "아직 확정적으로 말할 단계는 아닌데\n평소랑 움직임이 조금 다름.\n\n일단 소액 들어가 봄.",
        "likes": 1,
        "comments": [
            ("하린버핏", "“확정적으로 말할 단계 아님”\n“일단 들어가 봄”\n\n이 두 문장이 같이 있어도 되는 거야?", [
                ("민주풀악셀", "확정되고 들어가면 늦어."),
                ("하린버핏", "그러다 틀리면?"),
                ("민주풀악셀", "소액이라 괜찮아."),
                ("하린버핏", "네 소액 종목이 지금 몇 개인데?"),
            ]),
            ("성익테리움", "이런 걸 살 바에야 진짜 이더 사라.", [
                ("민주풀악셀", "오늘 처음으로 네 말이 조금 설득력 있다."),
                ("성익테리움", "드디어 금융 지능이 생겼네."),
            ]),
            ("주현PLUS", "SK증권도 SK니까 하이닉스 따라가는 거 아님?", [
                ("하린버핏", "그 논리면 SK 계열사 주가가 전부 같아야지."),
                ("주현PLUS", "가끔 시장이 논리대로 안 움직이잖아."),
                ("민주풀악셀", "주현이는 틀린 논리를 시장 탓으로 방어하네."),
            ]),
        ],
    },
    {
        "stock": ("037270.KS", "YG PLUS"),
        "title": "오늘 느낌이 다름",
        "author": "주현PLUS",
        "content": "거래량 조금 들어왔고\n밑에서 누가 계속 받는 것 같음.\n\n컴백 일정까지 나오면 진짜 시작할 수도 있음.",
        "likes": 1,
        "comments": [
            ("하린버핏", "지난주에도 느낌이 다르다고 하지 않았어?", [
                ("주현PLUS", "지난주는 예고편이고 오늘이 본편."),
                ("하린버핏", "지난달에는 뭐였는데?"),
                ("주현PLUS", "티저."),
            ]),
            ("민주풀악셀", "거래량 들어왔다는 말에 확인하러 갔는데\n평소보다 아주 조금 많은 수준이잖아.", [
                ("주현PLUS", "큰 거래량도 처음에는 작은 거래량으로 시작해."),
                ("민주풀악셀", "이런 식이면 모든 날이 시작이야."),
            ]),
            ("성익테리움", "그 돈이면 이더 샀으면 프로젝트 백서라도 있다.", [
                ("주현PLUS", "이더 백서 읽어봤어?"),
                ("성익테리움", "핵심은 알고 있지."),
                ("주현PLUS", "나도 YG 핵심은 알아. 컴백하면 됨."),
            ]),
            ("하린버핏", "처음 매수한 이유가 뭐였어?", [
                ("주현PLUS", "처음에는 차트가 좋아 보였고\n지금은 엔터 산업의 미래를 보고 있어."),
                ("민주풀악셀", "차트가 망가지니까 산업을 보기 시작했네."),
                ("주현PLUS", "투자 관점이 확장된 거지."),
            ]),
        ],
    },
    {
        "stock": ("037270.KS", "YG PLUS"),
        "title": "내가 뭐랬냐",
        "author": "주현PLUS",
        "content": "현재 +3.2%\n\n이제 시작이다.\n그동안 나 놀린 사람들 한 명씩 반성문 제출해라.",
        "likes": 2,
        "comments": [
            ("민주풀악셀", "네 손실률이 -28%에서 -25% 된 거 아니야?", [
                ("주현PLUS", "방향이 중요하지 숫자가 중요하냐?"),
                ("하린버핏", "투자에서는 숫자가 중요하지."),
            ]),
            ("성익테리움", "이더는 밤사이에 4% 올랐는데.", [
                ("주현PLUS", "내가 이더 이야기했냐?\n여기는 YG PLUS 토론방이다."),
                ("하린버핏", "네가 드디어 정상적인 말을 하네."),
            ]),
            ("민주풀악셀", "3% 오른 날 바로 글 쓰는 거 보니\n얼마나 오래 기다렸는지는 알겠다.", [
                ("주현PLUS", "오래 기다린 사람만이 상승을 누릴 자격이 있다."),
                ("성익테리움", "그 논리면 너는 거의 창업자야."),
            ]),
        ],
    },
    {
        "stock": None,
        "title": "성익이 오늘 조용하네",
        "author": "하린버핏",
        "content": "이더리움 밤사이에 많이 내린 것 같은데\n평소라면 아침부터 탈중앙화 이야기할 시간 아닌가?",
        "likes": 3,
        "comments": [
            ("민주풀악셀", "접속은 했는데 글만 안 쓰는 중일 듯.", [
                ("주현PLUS", "시장과 거리를 두는 것도 투자 전략이다."),
                ("하린버핏", "너는 왜 성익이 편을 들어?"),
                ("주현PLUS", "나도 자주 거리를 두거든. 계좌랑."),
            ]),
            ("성익테리움", "단기 가격 변동에는 관심 없음.", [
                ("하린버핏", "어제 4% 올랐을 때는 캡처 보냈잖아."),
                ("성익테리움", "상승은 채택의 증거고\n하락은 시장의 노이즈야."),
                ("민주풀악셀", "내가 종목 떨어질 때 하는 말이랑 똑같네."),
            ]),
            ("주현PLUS", "이더 살 돈이면 YG PLUS 샀으면 주식 수는 더 많았다.", [
                ("성익테리움", "수량이 중요한 게 아니라니까."),
                ("주현PLUS", "나도 이제 그 말 써야겠다."),
            ]),
        ],
    },
    {
        "stock": None,
        "title": "각자 포트폴리오 한 줄 평가해봄",
        "author": "민주풀악셀",
        "content": "하린: 대기업 임직원 지분 계좌\n성익: 실체 없는 인터넷 돌멩이\n주현: YG 비공식 구조대\n나: 미래 산업 선점형 포트폴리오\n\n반박받음.",
        "likes": 4,
        "comments": [
            ("하린버핏", "네 포트폴리오: 뉴스 알림 모음집.", [
                ("민주풀악셀", "뉴스가 곧 기회야."),
                ("하린버핏", "뉴스 뜬 다음에 샀잖아."),
            ]),
            ("성익테리움", "하린: 성장성 부족\n민주: 원칙 부족\n주현: 이유 부족\n나: 이더 충분", [
                ("주현PLUS", "너는 겸손이 부족함."),
                ("민주풀악셀", "그리고 현금도 부족한 것 같던데."),
            ]),
            ("주현PLUS", "내 포트폴리오는 집중투자임.", [
                ("하린버핏", "집중투자와 한 종목에 갇힌 건 달라."),
                ("주현PLUS", "결과 나오기 전까지는 구분 못 해."),
                ("성익테리움", "결과가 몇 년째 나오고 있잖아."),
            ]),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed AlphaPick community QA scenario posts, comments, replies, and likes."

    def handle(self, *args, **options):
        User = get_user_model()
        with transaction.atomic():
            users = {}
            for nickname, username in PERSONAS.items():
                user = User.objects.filter(nickname=nickname).first()
                if not user:
                    user = User.objects.filter(username=username).first()
                if not user:
                    user = User.objects.create_user(
                        username=username,
                        email=f"{username}@example.com",
                        password="AlphaPickQA123!",
                        nickname=nickname,
                        risk_type=User.RiskType.NEUTRAL,
                    )
                elif not user.nickname:
                    user.nickname = nickname
                    user.save(update_fields=["nickname"])
                ensure_avatar(user, nickname)
                users[nickname] = user

            max_likes = max(post["likes"] for post in POSTS)
            likers = []
            for index in range(max_likes):
                username = f"qa_liker_{index + 1:02d}"
                liker, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "nickname": "",
                        "email": f"{username}@example.com",
                        "risk_type": User.RiskType.NEUTRAL,
                    },
                )
                likers.append(liker)

            titles = [post["title"] for post in POSTS]
            Post.objects.filter(title__in=titles).delete()

            created_posts = 0
            created_comments = 0
            created_likes = 0
            base_time = timezone.now() - timedelta(hours=(len(POSTS) - 1) * 2)

            for post_index, payload in enumerate(POSTS):
                stock = None
                if payload["stock"]:
                    ticker, stock_name = payload["stock"]
                    stock = Stock.objects.filter(ticker=ticker).first() or Stock.objects.filter(name=stock_name).first()
                    if not stock:
                        self.stdout.write(self.style.WARNING(f"stock not found: {stock_name} ({ticker}), skipped"))
                        continue

                post = Post.objects.create(
                    stock=stock,
                    author=users[payload["author"]],
                    title=payload["title"],
                    content=payload["content"],
                )
                post_time = base_time + timedelta(hours=post_index * 2)
                Post.objects.filter(pk=post.pk).update(created_at=post_time, updated_at=post_time)
                created_posts += 1

                for liker in likers[: payload["likes"]]:
                    if liker.pk == post.author_id:
                        continue
                    PostLike.objects.create(user=liker, post=post)
                    created_likes += 1

                comment_order = 0
                for author_name, content, replies in payload["comments"]:
                    comment = Comment.objects.create(
                        post=post,
                        author=users[author_name],
                        content=content,
                    )
                    comment_time = post_time + timedelta(minutes=10 + comment_order * 7)
                    Comment.objects.filter(pk=comment.pk).update(created_at=comment_time)
                    created_comments += 1
                    comment_order += 1

                    for reply_author, reply_content in replies:
                        reply = Comment.objects.create(
                            post=post,
                            parent=comment,
                            author=users[reply_author],
                            content=reply_content,
                        )
                        reply_time = post_time + timedelta(minutes=10 + comment_order * 7)
                        Comment.objects.filter(pk=reply.pk).update(created_at=reply_time)
                        created_comments += 1
                        comment_order += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"community QA seeded: {created_posts} posts, {created_comments} comments/replies, {created_likes} likes."
            )
        )


def ensure_avatar(user, nickname):
    spec = AVATARS[nickname]
    relative_path = f"profiles/community_qa/{PERSONAS[nickname]}.png"
    output_path = settings.MEDIA_ROOT / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_avatar(output_path, nickname, spec)
    if user.profile_image.name != relative_path:
        user.profile_image.name = relative_path
        user.save(update_fields=["profile_image"])


def draw_avatar(path, nickname, spec):
    size = 512
    image = Image.new("RGB", (size, size), spec["bg"][0])
    pixels = image.load()
    start = hex_to_rgb(spec["bg"][0])
    end = hex_to_rgb(spec["bg"][1])
    for y in range(size):
        ratio = y / (size - 1)
        for x in range(size):
            drift = (x / (size - 1)) * 0.22
            amount = min(1, ratio * 0.78 + drift)
            pixels[x, y] = tuple(int(start[i] * (1 - amount) + end[i] * amount) for i in range(3))

    draw = ImageDraw.Draw(image)
    draw.ellipse((24, 24, 488, 488), outline=(255, 255, 255), width=8)

    kind = spec["kind"]
    if kind == "moth":
        draw_moth(draw)
    elif kind == "chairman":
        draw_chairman(draw)
    elif kind == "gungye":
        draw_gungye(draw)
    elif kind == "chart":
        draw_chart(draw)
    elif kind == "document":
        draw_document(draw)
    elif kind == "scissors":
        draw_scissors(draw)
    elif kind == "dividend":
        draw_dividend(draw)
    elif kind == "shopping":
        draw_shopping(draw)
    elif kind == "factory":
        draw_factory(draw)
    elif kind == "salaryman":
        draw_salaryman(draw)
    elif kind == "guard":
        draw_guard(draw)
    elif kind == "crypto":
        draw_crypto(draw)
    elif kind == "rocket":
        draw_rocket(draw)
    elif kind == "plus":
        draw_plus(draw)
    else:
        draw_minimal(draw)

    label_font = load_font(42)
    draw.rounded_rectangle((92, 408, 420, 462), radius=27, fill=(255, 255, 255))
    draw_centered_text(draw, spec["label"], label_font, (256, 415), hex_to_rgb(spec["bg"][0]), width=328)
    image.save(path, "PNG")


def draw_moth(draw):
    draw.ellipse((82, 152, 250, 362), fill="#fde68a", outline="#7c2d12", width=8)
    draw.ellipse((262, 152, 430, 362), fill="#fed7aa", outline="#7c2d12", width=8)
    draw.ellipse((210, 142, 302, 386), fill="#3f1d0b", outline="#fff7ed", width=5)
    draw.ellipse((230, 105, 282, 158), fill="#3f1d0b")
    draw.line((238, 112, 176, 56), fill="#fff7ed", width=7)
    draw.line((274, 112, 338, 56), fill="#fff7ed", width=7)
    draw.ellipse((166, 46, 190, 70), fill="#fff7ed")
    draw.ellipse((326, 46, 350, 70), fill="#fff7ed")
    for x in (140, 190, 320, 370):
        draw.ellipse((x, 235, x + 28, 263), fill="#7c2d12")


def draw_chairman(draw):
    draw.ellipse((174, 88, 338, 252), fill="#f1c27d")
    draw.arc((180, 70, 332, 190), 190, 350, fill="#111827", width=28)
    draw.rectangle((188, 168, 324, 188), fill="#111827")
    draw.ellipse((214, 182, 238, 206), fill="#020617")
    draw.ellipse((274, 182, 298, 206), fill="#020617")
    draw.line((236, 225, 276, 225), fill="#7f1d1d", width=6)
    draw.polygon([(128, 420), (206, 270), (306, 270), (384, 420)], fill="#0f172a")
    draw.polygon([(218, 284), (256, 356), (294, 284)], fill="#f8fafc")
    draw.polygon([(244, 334), (268, 334), (278, 420), (234, 420)], fill="#0ea5e9")
    draw.rounded_rectangle((138, 318, 374, 372), radius=18, outline="#facc15", width=6)


def draw_gungye(draw):
    draw.polygon([(104, 166), (174, 80), (256, 160), (338, 80), (408, 166)], fill="#facc15", outline="#713f12")
    draw.rectangle((112, 162, 400, 208), fill="#facc15", outline="#713f12", width=6)
    draw.ellipse((158, 142, 354, 338), fill="#f1c27d", outline="#713f12", width=6)
    draw.rectangle((160, 202, 352, 246), fill="#111827")
    draw.ellipse((232, 184, 280, 232), fill="#f8fafc")
    draw.ellipse((246, 198, 266, 218), fill="#020617")
    draw.line((216, 286, 296, 286), fill="#7f1d1d", width=7)
    draw.polygon([(138, 422), (202, 334), (310, 334), (374, 422)], fill="#7c2d12")


def draw_chart(draw):
    draw.rounded_rectangle((94, 116, 418, 376), radius=22, fill="#f8fafc")
    draw.line((132, 334, 384, 334), fill="#94a3b8", width=5)
    draw.line((132, 334, 132, 158), fill="#94a3b8", width=5)
    points = [(150, 304), (206, 260), (250, 278), (300, 198), (370, 146)]
    draw.line(points, fill="#0891b2", width=14, joint="curve")
    for x, y in points:
        draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill="#0f172a")
    draw.polygon([(370, 146), (346, 148), (372, 118)], fill="#0891b2")


def draw_document(draw):
    draw.rounded_rectangle((128, 80, 384, 402), radius=20, fill="#f8fafc")
    draw.polygon([(318, 80), (384, 146), (318, 146)], fill="#bfdbfe")
    for y in (178, 222, 266, 310):
        draw.rounded_rectangle((164, y, 348, y + 16), radius=8, fill="#2563eb")
    draw.ellipse((154, 348, 216, 410), fill="#22c55e")
    draw.line((168, 378, 184, 394), fill="#f8fafc", width=8)
    draw.line((184, 394, 206, 360), fill="#f8fafc", width=8)


def draw_scissors(draw):
    draw.line((178, 142, 344, 350), fill="#f8fafc", width=22)
    draw.line((334, 142, 168, 350), fill="#f8fafc", width=22)
    draw.line((178, 142, 344, 350), fill="#7c3aed", width=8)
    draw.line((334, 142, 168, 350), fill="#7c3aed", width=8)
    draw.ellipse((118, 310, 204, 396), outline="#f8fafc", width=18)
    draw.ellipse((308, 310, 394, 396), outline="#f8fafc", width=18)
    draw.ellipse((238, 238, 274, 274), fill="#facc15")


def draw_dividend(draw):
    draw.ellipse((128, 96, 384, 352), fill="#facc15", outline="#854d0e", width=12)
    draw.ellipse((164, 132, 348, 316), outline="#fff7ed", width=9)
    won_font = load_font(142)
    draw_centered_text(draw, "₩", won_font, (256, 168), "#064e3b", width=180)
    draw.rounded_rectangle((142, 334, 370, 384), radius=25, fill="#064e3b")
    draw_centered_text(draw, "CASH FLOW", load_font(27), (256, 344), "#fef3c7", width=220)


def draw_shopping(draw):
    draw.rounded_rectangle((132, 168, 380, 372), radius=28, fill="#f8fafc")
    draw.arc((182, 96, 330, 236), 180, 360, fill="#f8fafc", width=18)
    draw.line((256, 210, 256, 318), fill="#16a34a", width=18)
    draw.line((202, 264, 310, 264), fill="#16a34a", width=18)
    draw.ellipse((158, 386, 202, 430), fill="#052e16")
    draw.ellipse((310, 386, 354, 430), fill="#052e16")


def draw_factory(draw):
    draw.rectangle((86, 258, 426, 390), fill="#78350f")
    draw.polygon([(86, 258), (156, 194), (226, 258), (296, 194), (366, 258)], fill="#b45309")
    draw.rectangle((342, 112, 396, 258), fill="#451a03")
    draw.ellipse((330, 62, 384, 112), fill="#fef3c7")
    draw.ellipse((362, 38, 440, 96), fill="#fef3c7")
    for x in (122, 202, 282, 362):
        draw.rectangle((x, 300, x + 38, 352), fill="#fde68a")
    draw.ellipse((216, 152, 296, 232), outline="#fef3c7", width=12)


def draw_salaryman(draw):
    draw.ellipse((176, 94, 336, 254), fill="#f1c27d")
    draw.arc((172, 72, 340, 184), 190, 350, fill="#1e293b", width=30)
    draw.ellipse((218, 180, 238, 200), fill="#020617")
    draw.ellipse((274, 180, 294, 200), fill="#020617")
    draw.line((232, 226, 282, 226), fill="#7f1d1d", width=6)
    draw.rounded_rectangle((138, 286, 374, 426), radius=38, fill="#0f172a")
    draw.polygon([(218, 286), (256, 360), (294, 286)], fill="#f8fafc")
    draw.rectangle((130, 320, 382, 366), fill="#22c55e")
    draw_centered_text(draw, "PAYDAY", load_font(34), (256, 325), "#052e16", width=240)


def draw_guard(draw):
    draw.rounded_rectangle((132, 112, 380, 378), radius=42, fill="#f8fafc")
    draw.polygon([(256, 86), (366, 134), (348, 278), (256, 402), (164, 278), (146, 134)], fill="#14b8a6", outline="#064e3b")
    draw.polygon([(256, 130), (326, 160), (314, 264), (256, 354), (198, 264), (186, 160)], fill="#ccfbf1")
    draw_centered_text(draw, "AVG", load_font(68), (256, 206), "#0f766e", width=180)


def draw_crypto(draw):
    draw.polygon([(256, 72), (356, 244), (256, 300), (156, 244)], fill="#e9d5ff", outline="#4c1d95")
    draw.polygon([(256, 72), (256, 300), (156, 244)], fill="#c4b5fd")
    draw.polygon([(256, 320), (356, 268), (256, 438), (156, 268)], fill="#ddd6fe", outline="#4c1d95")
    draw.polygon([(256, 320), (256, 438), (156, 268)], fill="#a78bfa")
    draw_centered_text(draw, "ETH", load_font(54), (256, 214), "#1e1b4b", width=180)


def draw_rocket(draw):
    draw.polygon([(256, 70), (332, 230), (306, 358), (206, 358), (180, 230)], fill="#f8fafc", outline="#7f1d1d")
    draw.ellipse((224, 168, 288, 232), fill="#38bdf8", outline="#0f172a", width=5)
    draw.polygon([(206, 306), (118, 374), (214, 360)], fill="#ef4444")
    draw.polygon([(306, 306), (394, 374), (298, 360)], fill="#ef4444")
    draw.polygon([(218, 358), (256, 456), (294, 358)], fill="#f97316")
    draw.polygon([(236, 358), (256, 420), (276, 358)], fill="#fef3c7")
    draw_centered_text(draw, "재료", load_font(42), (256, 252), "#7f1d1d", width=180)


def draw_plus(draw):
    draw.ellipse((156, 92, 356, 292), fill="#fce7f3", outline="#581c87", width=8)
    draw.arc((164, 64, 348, 210), 200, 340, fill="#111827", width=24)
    draw.ellipse((206, 172, 226, 194), fill="#111827")
    draw.ellipse((286, 172, 306, 194), fill="#111827")
    draw.line((224, 232, 288, 232), fill="#be185d", width=6)
    draw.rounded_rectangle((130, 296, 382, 406), radius=42, fill="#581c87")
    draw.line((256, 324, 256, 378), fill="#f0abfc", width=18)
    draw.line((229, 351, 283, 351), fill="#f0abfc", width=18)
    draw_centered_text(draw, "YG", load_font(46), (256, 100), "#581c87", width=160)


def draw_minimal(draw):
    draw.ellipse((128, 128, 384, 384), fill="#f8fafc")
    draw_centered_text(draw, ".", load_font(220), (256, 104), "#be185d", width=180)


def draw_centered_text(draw, text, font, center, fill, width):
    box = draw.textbbox((0, 0), text, font=font)
    x = center[0] - (box[2] - box[0]) / 2
    y = center[1]
    draw.text((x, y), text, font=font, fill=fill)


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def load_font(size):
    candidates = [
        settings.BASE_DIR.parent / "frontend" / "src" / "assets" / "fonts" / "SUIT-Heavy.woff2",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()
