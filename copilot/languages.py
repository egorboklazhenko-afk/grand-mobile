import re
from .retrieval import normalize

def detect(text):
    t = normalize(text)
    scores = {
        'kk': sum(t.count(w) for w in ['қ','ғ','ң','ә','ө','ұ','ү','і','көмек','сәлем','аккаунтым','беріңіз','жоқ','ойын']),
        'uz': sum(t.count(w) for w in ['salom','yordam','iltimos','hisobim','akkauntim','qanday','menga',"o‘","o'","g'",'qoldim','kelmadi','o‘yin']),
        'ru': len(re.findall('[а-я]', t)) / 8,
        'en': sum(len(re.findall(r'\b'+w+r'\b',t)) for w in ['help','please','my','account','stuck','how','payment','insult','cheater','banned']),
        'es': sum(len(re.findall(r'\b'+w+r'\b',t)) for w in ['hola','ayuda','cuenta','como','cómo','jugador','gracias','pago']),
        'pt': sum(len(re.findall(r'\b'+w+r'\b',t)) for w in ['olá','ajuda','minha','conta','jogador','obrigado','pagamento','não']),
    }
    if scores['kk'] >= 2:
        return 'kk'
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'und'

# Human-reviewable wording. Native-speaker review is still required for competition.
COPY = {
'ru': {
 'hello':'Здравствуйте!', 'claim':'Спасибо за обращение. Описанная ситуация пока не подтверждена.',
 'evidence':'Материалы отмечены как приложенные, но их содержимое мне недоступно.',
 'missing':'Укажите ник игрока, сервер, время события и приложите запись или скриншоты, если они есть.',
 'human':'Для решения требуется проверка администратором.',
 'account':'Не сообщайте пароль и коды подтверждения. Укажите сервер, ник и время потери доступа.',
 'payment':'Укажите сервер, время платежа и номер операции. Не присылайте полный номер карты, CVV и коды подтверждения.',
 'appeal':'Укажите сервер, ник, время наказания и причину несогласия.',
 'question':'Уточните, что именно вы хотите сделать и на каком этапе возник вопрос.',
 'help':'Опишите, где вы застряли или что перестало работать; укажите сервер и время события.',
 'empty':'Опишите проблему одним сообщением: что произошло, где и когда.',
 'rule':'Для проверки ситуации релевантен пункт {ref} раздела «{section}». Это основание для проверки, а не подтверждение нарушения.',
 'duplicate':'Похожее обращение от вас уже зарегистрировано за последний час. Уточните, появились ли новые сведения.',
},
'kk': {
 'hello':'Сәлеметсіз бе!', 'claim':'Өтінішіңізге рақмет. Сипатталған жағдай әлі расталған жоқ.',
 'evidence':'Тіркемелер бар деп көрсетілген, бірақ олардың мазмұны маған қолжетімсіз.',
 'missing':'Ойыншының атын, серверді, оқиға уақытын көрсетіп, бар болса бейне немесе скриншот тіркеңіз.',
 'human':'Шешім қабылдау үшін әкімшінің тексеруі қажет.',
 'account':'Құпиясөз бен растау кодтарын жібермеңіз. Серверді, ойыншы атын және кіру мүмкіндігін жоғалтқан уақытты көрсетіңіз.',
 'payment':'Серверді, төлем уақытын және операция нөмірін көрсетіңіз. Картаның толық нөмірін, CVV немесе растау кодтарын жібермеңіз.',
 'appeal':'Серверді, ойыншы атын, жаза уақытын және келіспеу себебін көрсетіңіз.',
 'question':'Не істегіңіз келетінін және сұрақ қай кезеңде туындағанын нақтылаңыз.',
 'help':'Қай жерде тұрып қалғаныңызды немесе не істемей тұрғанын сипаттап, сервер мен уақытты көрсетіңіз.',
 'empty':'Мәселені бір хабарламада сипаттаңыз: не болды, қайда және қашан?',
 'rule':'Жағдайды тексеру үшін ереженің {ref} тармағы маңызды. Бұл бұзушылықтың расталғанын білдірмейді.',
 'duplicate':'Соңғы сағатта сізден ұқсас өтініш тіркелген. Жаңа мәліметтер бар ма?',
},
'uz': {
 'hello':'Assalomu alaykum!', 'claim':'Murojaatingiz uchun rahmat. Tasvirlangan holat hali tasdiqlanmagan.',
 'evidence':"Ilovalar borligi ko‘rsatilgan, ammo ularning mazmunini ko‘ra olmayman.",
 'missing':"O‘yinchi nomi, server va voqea vaqtini yozing; mavjud bo‘lsa, video yoki skrinshot ilova qiling.",
 'human':'Qaror qabul qilish uchun administrator tekshiruvi zarur.',
 'account':"Parol va tasdiqlash kodlarini yubormang. Server, o‘yinchi nomi va kirish yo‘qolgan vaqtni yozing.",
 'payment':"Server, to‘lov vaqti va operatsiya raqamini yozing. Kartaning to‘liq raqami, CVV yoki tasdiqlash kodlarini yubormang.",
 'appeal':"Server, o‘yinchi nomi, jazo vaqti va e’tirozingiz sababini yozing.",
 'question':"Nima qilmoqchi ekaningizni va qaysi bosqichda savol tug‘ilganini aniqlashtiring.",
 'help':"Qayerda qotib qolganingizni yoki nima ishlamayotganini tasvirlab, server va vaqtni yozing.",
 'empty':"Muammoni bitta xabarda tushuntiring: nima, qayerda va qachon sodir bo‘ldi?",
 'rule':"Holatni tekshirish uchun qoidalarning {ref}-bandi muhim. Bu qoidabuzarlik tasdiqlanganini anglatmaydi.",
 'duplicate':"Oxirgi bir soatda sizdan o‘xshash murojaat qayd etilgan. Yangi ma’lumot bormi?",
},
'en': {
 'hello':'Hello!', 'claim':'Thank you for your report. The described events have not been verified.',
 'evidence':'Attachments are listed, but I cannot inspect their contents.',
 'missing':'Please provide the player name, server, incident time and any available recording or screenshots.',
 'human':'An administrator must review this before a decision can be made.',
 'account':'Do not share passwords or verification codes. Provide your server, player name and when access was lost.',
 'payment':'Provide the server, payment time and transaction reference. Do not send full card numbers, CVV or verification codes.',
 'appeal':'Provide the server, player name, penalty time and grounds for your appeal.',
 'question':'Please clarify what you want to do and where you need help.',
 'help':'Describe where you are stuck or what stopped working, and provide the server and incident time.',
 'empty':'Please describe the issue in one message: what happened, where and when?',
 'rule':'Rule {ref} is relevant for reviewing this report. This is not confirmation of a violation.',
 'duplicate':'A similar request from you was recorded within the last hour. Do you have new information?',
},
'es': {
 'hello':'¡Hola!', 'claim':'Gracias por tu mensaje. Los hechos descritos aún no se han verificado.',
 'evidence':'Hay archivos adjuntos indicados, pero no puedo ver su contenido.',
 'missing':'Indica el nombre del jugador, servidor, hora y adjunta grabaciones o capturas si las tienes.',
 'human':'Un administrador debe revisar el caso antes de tomar una decisión.',
 'account':'No compartas contraseñas ni códigos de verificación. Indica servidor, nombre y cuándo perdiste el acceso.',
 'payment':'Indica servidor, hora del pago y referencia de la operación. No envíes el número completo de tarjeta, CVV ni códigos.',
 'appeal':'Indica servidor, nombre, hora de la sanción y motivo de la apelación.',
 'question':'Aclara qué quieres hacer y en qué paso necesitas ayuda.',
 'help':'Describe dónde estás atascado o qué dejó de funcionar e indica servidor y hora.',
 'empty':'Describe el problema en un mensaje: qué pasó, dónde y cuándo.',
 'rule':'La regla {ref} es pertinente para revisar el caso. Esto no confirma una infracción.',
 'duplicate':'Ya se registró una solicitud similar tuya durante la última hora. ¿Hay información nueva?',
},
'pt': {
 'hello':'Olá!', 'claim':'Obrigado pela mensagem. Os fatos descritos ainda não foram verificados.',
 'evidence':'Há anexos indicados, mas não consigo verificar o conteúdo.',
 'missing':'Informe nome do jogador, servidor, horário e envie gravações ou capturas, se disponíveis.',
 'human':'Um administrador precisa analisar o caso antes de tomar uma decisão.',
 'account':'Não compartilhe senhas ou códigos de verificação. Informe servidor, nome e quando perdeu o acesso.',
 'payment':'Informe servidor, horário do pagamento e referência da transação. Não envie número completo do cartão, CVV ou códigos.',
 'appeal':'Informe servidor, nome, horário da punição e motivo do recurso.',
 'question':'Esclareça o que deseja fazer e em qual etapa precisa de ajuda.',
 'help':'Descreva onde ficou preso ou o que parou de funcionar e informe servidor e horário.',
 'empty':'Descreva o problema em uma mensagem: o que aconteceu, onde e quando.',
 'rule':'A regra {ref} é relevante para analisar o caso. Isso não confirma uma infração.',
 'duplicate':'Uma solicitação semelhante sua foi registrada na última hora. Há informações novas?',
}}
