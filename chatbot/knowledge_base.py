"""Bilingual knowledge for MGOWELO AMCOS — keyword fallback + OpenRouter system prompt."""
import re

KNOWLEDGE = [
    {
        'keywords': ['mgowelo', 'amcos', 'mfumo', 'system', 'hiki', 'hii', 'overview'],
        'answer_sw': (
            'MGOWELO AMCOS ni mfumo kamili wa usimamizi wa vyama vya ushirika vya kilimo (AMCOS/SACCO). '
            'Unajumuisha wanachama, malipo, akiba, mikopo, hisa, uhasibu, mikutano, ripoti, na taarifa.'
        ),
        'answer_en': (
            'MGOWELO AMCOS is a full management system for agricultural marketing cooperatives (AMCOS/SACCO). '
            'It covers members, payments, savings, loans, shares, accounting, meetings, reports, and notifications.'
        ),
    },
    {
        'keywords': ['login', 'ingia', 'sign in', 'password', 'nywila', 'username', 'force password', 'reset password'],
        'answer_sw': (
            'Ingia kwa namba ya simu au username na nywila. Ikiwa umesahau nywila, tumia "Forgot Password" (OTP). '
            'Wanachama waliosajiliwa na admin lazima waweke nywila mpya mara ya kwanza kabla ya dashboard.'
        ),
        'answer_en': (
            'Log in with phone or username and password. Use "Forgot Password" for OTP reset. '
            'Members registered by admin must set a new password on first login before accessing the dashboard.'
        ),
    },
    {
        'keywords': ['register', 'usajili', 'sajili', 'jiunge', 'signup', 'member registration'],
        'answer_sw': (
            'Usajili wa mwanachama: Jiunga (register member) — lipa ada, ingiza TXN ID, jaza taarifa na akaunti. '
            'Admin: Members → Sajili Mwanachama — lazima namba ya malipo (au Demo TXN), weka nywila ya muda kwa mwanachama.'
        ),
        'answer_en': (
            'Member registration: public Register Member flow with fee + transaction ID. '
            'Admin: Members → Register Member — payment reference required (or Demo TXN), set temporary password for member.'
        ),
    },
    {
        'keywords': ['demo txn', 'demo', 'transaction id', 'txn', 'namba ya malipo', 'payment reference'],
        'answer_sw': (
            'Kwenye usajili wa admin, bonyeza "Demo TXN" kuzalisha namba ya majaribio (mfano DEMOXXXXXXXXXX) '
            'wakati hakuna API halisi ya malipo. Namba hiyo inathibitishwa kiotomatiki kwa ada ya usajili.'
        ),
        'answer_en': (
            'On admin registration, click "Demo TXN" to generate a test payment reference when no live payment API exists. '
            'It is auto-verified for the registration fee.'
        ),
    },
    {
        'keywords': ['role', 'wajibu', 'jukumu', 'mwenyekiti', 'chairperson', 'pa-rc', 'parc', 'katibu', 'secretary',
                     'mhazini', 'treasurer', 'mhasibu', 'accountant', 'bodi', 'board', 'carder', 'admin', 'tcdc'],
        'answer_sw': (
            'Majukumu: PA-RC (mikopo/idhini), Katibu (wanachama/mikutano), Mhazini (malipo), Mhasibu (ripoti), '
            'Afisa Mikopo, Mkaguzi, TCDC Wilaya/Mkoa (ufuatiliaji kusoma tu), Mjumbe wa Bodi, Carder (vitambulisho), '
            'Mwanachama, Cooperative Admin, Super Admin.'
        ),
        'answer_en': (
            'Roles: PA-RC (loans/approval), Secretary (members/meetings), Treasurer (payments), Accountant (reports), '
            'Loan Officer, Auditor, TCDC District/Regional (read-only oversight), Board Member, Carder (ID cards), '
            'Member, Cooperative Admin, Super Admin.'
        ),
    },
    {
        'keywords': ['payment', 'malipo', 'lipa', 'mpesa', 'mixx', 'halopesa', 'airtel', 'ussd',
                     'invoice', 'receipt', 'stakabadhi', 'registration fee', 'ada'],
        'answer_sw': (
            'Malipo: M-Pesa, Mixx, HaloPesa, Airtel, SELCOM, benki, cash. Wasilisha TXN ID kwenye Malipo. '
            'Ada ya usajili lazima ithibitishwe kabla ya kuunda mwanachama (admin au kujiunga). Stakabadhi na invoice zinapatikana baada ya uthibitisho.'
        ),
        'answer_en': (
            'Payments: M-Pesa, Mixx, HaloPesa, Airtel, SELCOM, bank, cash. Submit transaction ID under Payments. '
            'Registration fee must be verified before creating a member. Receipts and invoices after confirmation.'
        ),
    },
    {
        'keywords': ['loan', 'mkopo', 'mikopo', 'kopa', 'borrow'],
        'answer_sw': 'Omba mkopo kwenye Mikopo. Kiasi hakiwezi kuzidi thamani ya hisa zako (lazima uwe na hisa). PA-RC huidhinisha.',
        'answer_en': 'Apply under Loans. Loan amount cannot exceed your total share value (shares required). PA-RC approves.',
    },
    {
        'keywords': ['savings', 'akiba', 'deposit', 'weka'],
        'answer_sw': 'Akiba: weka kupitia malipo au taslimu, angalia historia kwenye Akiba.',
        'answer_en': 'Savings: deposit via payment or cash; view history under Savings.',
    },
    {
        'keywords': ['share', 'hisa', 'dividend', 'dividendi'],
        'answer_sw': 'Hisa = umiliki; nunua kwenye Hisa. Dividendi hugawanywa kulingana na hisa.',
        'answer_en': 'Shares = ownership; buy under Shares. Dividends distributed by shareholding.',
    },
    {
        'keywords': ['id card', 'vitambulisho', 'kadi', 'mgw'],
        'answer_sw': 'ID: MGW-YYYY-NNNN baada ya idhini. Chapisha kwenye Vitambulisho au ukurasa wa mwanachama (QR).',
        'answer_en': 'ID format MGW-YYYY-NNNN after approval. Print from ID Cards or member page (QR).',
    },
    {
        'keywords': ['meeting', 'mkutano', 'mikutano', 'governance', 'uongozi'],
        'answer_sw': 'Mikutano na uongozi: panga na Katibu, angalia ajenda/dakika kwenye Mikutano.',
        'answer_en': 'Meetings & governance: schedule as Secretary; view agenda/minutes under Meetings.',
    },
    {
        'keywords': ['report', 'ripoti', 'accounting', 'uhasibu', 'mizania'],
        'answer_sw': 'Ripoti na Uhasibu: mapato, matumizi, mizania, ripoti za wanachama/malipo.',
        'answer_en': 'Reports & Accounting: income, expenses, balance sheet, member/payment reports.',
    },
    {
        'keywords': ['notification', 'sms', 'ujumbe', 'message', 'chat', 'msaidizi'],
        'answer_sw': 'Taarifa, ujumbe, SMS baada ya malipo. AMCOS AI (chini kulia) kwa msaada wa mfumo.',
        'answer_en': 'Notifications, messages, SMS after payments. AMCOS AI (bottom-right) for system help.',
    },
    {
        'keywords': ['cooperative', 'ushirika', 'branch', 'tawi'],
        'answer_sw': 'Ushirika na matawi: usimamizi wa vyama vingi, kila tawi na wanachama wake.',
        'answer_en': 'Cooperatives & branches: multi-coop support; each branch with its members.',
    },
    {
        'keywords': ['approve', 'idhini', 'reject', 'kataa', 'pending', 'payment_confirmed'],
        'answer_sw': 'Mwanachama: pending → payment_confirmed (baada ya ada) → active (baada ya idhini na ID).',
        'answer_en': 'Member flow: pending → payment_confirmed (after fee) → active (after approval & ID).',
    },
    {
        'keywords': ['help', 'msaada', 'contact', 'wasiliana'],
        'answer_sw': 'Wasiliana na afisa wa ushirika au tumia ujumbe/notifications ndani ya mfumo.',
        'answer_en': 'Contact your cooperative officer or use in-system messages/notifications.',
    },
]

MODULE_GUIDE_SW = """
MODULI ZA MFUMO (njia kuu):
- Dashboard (/dashboard/) — muhtasari wa shughuli
- Wanachama (/members/) — orodha, sajili, idhini, vitambulisho, KYC
- Malipo (/payments/) — orodha, wasilisha TXN, thibitisha, invoice, stakabadhi
- Akiba (/savings/) — amana, uondoaji, historia
- Mikopo (/loans/) — omba, idhini, malipo ya mkopo
- Hisa (/shares/) — ununuzi, salio
- Uhasibu (/accounting/) — mapato, matumizi, shughuli
- Mikutano (/governance/meetings/) — ratiba, ajenda
- Ripoti (/reports/) — ripoti za fedha na wanachama
- Taarifa (/notifications/) — arifa na ujumbe
- Usajili (/auth/register/member/) — mwanachama kujiunga
- Admin sajili mwanachama: /members/create/ (malipo + nywila ya muda)
"""

MODULE_GUIDE_EN = """
SYSTEM MODULES (main paths):
- Dashboard (/dashboard/) — activity overview
- Members (/members/) — list, register, approve, ID cards, KYC
- Payments (/payments/) — list, submit TXN, verify, invoices, receipts
- Savings (/savings/) — deposits, withdrawals, history
- Loans (/loans/) — apply, approve, repayments
- Shares (/shares/) — purchase, balance
- Accounting (/accounting/) — income, expenses, ledger
- Meetings (/governance/meetings/) — schedule, agenda
- Reports (/reports/) — financial and member reports
- Notifications (/notifications/) — alerts and messages
- Self-register: /auth/register/member/
- Admin register member: /members/create/ (payment ref + temp password)
"""


GUEST_TOPICS_SW = """
- MGOWELO AMCOS ni ushirika wa kilimo na masoko huko Iringa, Tanzania.
- Wanachama wanaweza kujiunga kupitia ukurasa wa "Jiunga na Ushirika" / usajili wa mwanachama.
- Baada ya usajili, ingia kwenye mfumo kwa simu au username na nywila.
- Huduma za jumla: akiba, hisa, mikopo, malipo, vitambulisho, mikutano.
- Kwa maelezo ya akaunti yako (salio, mkopo, malipo), lazima uingie kwanza.
"""

GUEST_TOPICS_EN = """
- MGOWELO AMCOS is an agricultural marketing cooperative in Iringa, Tanzania.
- Members can join via "Join as Member" / member registration on the website.
- After registering, sign in with phone or username and password.
- General services: savings, shares, loans, payments, ID cards, meetings.
- For your own account details (balance, loan, payments), you must sign in first.
"""


def build_system_prompt(lang='sw', guest=False):
    """Full system context for OpenRouter."""
    lang_instruction = (
        'Jibu kwa Kiswahili sanifu, kwa ufupi na uwazi. Tumia hatua za namba inapohitajika.'
        if lang == 'sw'
        else 'Reply in clear English, concise and practical. Use numbered steps when helpful.'
    )

    if guest:
        topics = GUEST_TOPICS_SW if lang == 'sw' else GUEST_TOPICS_EN
        return f"""You are AMCOS AI, the public assistant for MGOWELO AMCOS (Agricultural Marketing Cooperative Society).

{lang_instruction}

VISITOR MODE (not logged in):
- Give only general, public information about the cooperative and how to join or sign in.
- Do NOT describe staff-only menus, internal approvals, or member-specific data.
- Do NOT guess the visitor's role, balance, or member number.
- If they ask about their personal account, loans, or payments, politely ask them to sign in first.

PUBLIC INFO:
{topics}
"""

    module_guide = MODULE_GUIDE_SW if lang == 'sw' else MODULE_GUIDE_EN
    topics = []
    for item in KNOWLEDGE:
        ans = item.get('answer_sw' if lang == 'sw' else 'answer_en', '')
        topics.append(f"- {ans}")
    topics_text = '\n'.join(topics[:20])

    return f"""You are AMCOS AI, the official assistant for MGOWELO AMCOS cooperative management system.

{lang_instruction}

RULES:
- Only answer about this system: members, payments, loans, savings, shares, accounting, meetings, reports, roles, registration.
- Do not invent features that are not listed below.
- If unsure, suggest contacting the cooperative officer or secretary.
- Be helpful to both farmers (wanachama) and staff (katibu, mhazini, PA-RC, admin).
- The user is logged in; you may tailor answers to their role when relevant.

{module_guide}

KEY FEATURES:
{topics_text}
"""


def find_answer(question):
    question_lower = question.lower().strip()
    for item in KNOWLEDGE:
        for kw in item['keywords']:
            if kw in question_lower:
                return item
    words = re.findall(r'\w+', question_lower)
    best_match = None
    best_count = 0
    for item in KNOWLEDGE:
        count = 0
        for kw in item['keywords']:
            for word in words:
                for part in kw.split():
                    if len(part) > 2 and len(word) > 2 and (part in word or word in part):
                        count += 1
        if count > best_count:
            best_count = count
            best_match = item
    if best_count >= 1:
        return best_match
    return None


def get_response(question, lang='en', guest=False):
    q = (question or '').lower()
    personal_hints = (
        'salio', 'balance', 'mkopo wangu', 'my loan', 'malipo yangu', 'my payment',
        'akaunti yangu', 'my account', 'dashboard yangu', 'member number yangu',
    )
    if guest and any(h in q for h in personal_hints):
        if lang == 'en':
            return (
                'Please sign in first to see your personal account, loans, or payments. '
                'I can only give general information about MGOWELO AMCOS while you are a visitor.'
            )
        return (
            'Tafadhali ingia kwanza ili uone akaunti yako, mikopo, au malipo. '
            'Nikiwa mgeni naweza kutoa tu taarifa za jumla kuhusu MGOWELO AMCOS.'
        )

    if guest:
        guest_items = [
            {
                'keywords': ['jiunga', 'register', 'join', 'usajili', 'member'],
                'answer_sw': 'Jiunga kupitia "Jiunga na Ushirika" kwenye ukurasa wa mwanzo, jaza taarifa na malipo ya usajili, kisha ingia kwa simu na nywila.',
                'answer_en': 'Join via "Join as Member" on the home page, complete registration and fee payment, then sign in with your phone and password.',
            },
            {
                'keywords': ['login', 'ingia', 'sign in'],
                'answer_sw': 'Bonyeza "Ingia kwenye Mfumo" kwenye ukurasa wa mwanzo. Tumia namba ya simu au username na nywila uliyosajiliwa.',
                'answer_en': 'Click "Sign In to System" on the home page. Use your registered phone number or username and password.',
            },
            {
                'keywords': ['amcos', 'mgowelo', 'ni nini', 'what is'],
                'answer_sw': 'MGOWELO AMCOS ni ushirika wa kilimo na masoko huko Iringa — wanachama wanashiriki katika akiba, hisa, mikopo, na masoko ya mazao.',
                'answer_en': 'MGOWELO AMCOS is an agricultural marketing cooperative in Iringa — members participate in savings, shares, loans, and crop marketing.',
            },
        ]
        for item in guest_items:
            for kw in item['keywords']:
                if kw in q:
                    return item['answer_en'] if lang == 'en' else item['answer_sw']

    result = find_answer(question)
    if result and not guest:
        if lang == 'en' and 'answer_en' in result:
            return result['answer_en']
        return result['answer_sw']
    if guest:
        if lang == 'en':
            return (
                'I am AMCOS AI for MGOWELO AMCOS. I can explain what the cooperative does, '
                'how to join, and how to sign in. Sign in for questions about your own account.'
            )
        return (
            'Mimi ni AMCOS AI wa MGOWELO AMCOS. Ninaweza kueleza ushirika unachofanya, '
            'jinsi ya kujiunga, na kuingia. Ingia kwa maswali kuhusu akaunti yako binafsi.'
        )
    if lang == 'en':
        return (
            "I'm AMCOS AI for MGOWELO AMCOS. Ask about members, payments, loans, savings, shares, "
            "ID cards, registration, meetings, reports, or roles."
        )
    return (
        "Mimi ni AMCOS AI wa MGOWELO AMCOS. Uliza kuhusu wanachama, malipo, mikopo, akiba, hisa, "
        "vitambulisho, usajili, mikutano, ripoti, au majukumu."
    )
