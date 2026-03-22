from django.core.management.base import BaseCommand
from apps.ethics.models import DisclaimerTemplate, EthicsRule


class Command(BaseCommand):
    help = 'Seed disclaimer templates and ethics rules'

    def handle(self, *args, **options):
        self.seed_disclaimers()
        self.seed_ethics_rules()

    def seed_disclaimers(self):
        disclaimers = [
            {
                'context': 'legal_query',
                'english_text': '⚠️ KNOWLEDGE ONLY: This information is provided for legal awareness purposes only. CaseIQ does not provide legal advice. Laws may have been amended. Please consult a qualified advocate for guidance specific to your situation.',
                'hindi_text': '⚠️ केवल जानकारी: यह जानकारी केवल कानूनी जागरूकता के उद्देश्य से दी गई है। CaseIQ कानूनी सलाह नहीं देता। कृपया अपनी स्थिति के लिए किसी योग्य अधिवक्ता से परामर्श लें।',
                'marathi_text': '⚠️ केवल माहिती: ही माहिती केवल कायदेशीर जागरूकतेसाठी दिली आहे। CaseIQ कायदेशीर सल्ला देत नाही। कृपया आपल्या परिस्थितीसाठी योग्य वकिलाचा सल्ला घ्या।',
            },
            {
                'context': 'complaint',
                'english_text': '⚠️ DRAFT ONLY: This complaint draft is generated for reference purposes only. CaseIQ does not provide legal advice. Please review with a qualified advocate before submission. The draft may need modification based on specific circumstances.',
                'hindi_text': '⚠️ केवल मसौदा: यह शिकायत मसौदा केवल संदर्भ के लिए तैयार किया गया है। दाखिल करने से पहले किसी योग्य अधिवक्ता से समीक्षा करवाएं।',
                'marathi_text': '⚠️ केवल मसुदा: हा तक्रार मसुदा केवल संदर्भासाठी तयार केला आहे। सादर करण्यापूर्वी योग्य वकिलाकडून तपासा।',
            },
            {
                'context': 'knowledge',
                'english_text': '⚠️ FOR AWARENESS ONLY: Legal provisions shown are for educational purposes. CaseIQ provides verified legal knowledge, not legal advice. Laws are subject to amendments and judicial interpretation.',
                'hindi_text': '⚠️ केवल जागरूकता के लिए: दिखाए गए कानूनी प्रावधान शैक्षिक उद्देश्यों के लिए हैं। CaseIQ सत्यापित कानूनी जानकारी प्रदान करता है, कानूनी सलाह नहीं।',
                'marathi_text': '',
            },
            {
                'context': 'general',
                'english_text': '⚠️ CaseIQ provides legal awareness and knowledge only. This is not legal advice. For legal guidance, please consult a qualified advocate.',
                'hindi_text': '⚠️ CaseIQ केवल कानूनी जागरूकता और ज्ञान प्रदान करता है। यह कानूनी सलाह नहीं है।',
                'marathi_text': '',
            },
        ]

        for d in disclaimers:
            obj, created = DisclaimerTemplate.objects.update_or_create(
                context=d['context'],
                defaults=d
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status} disclaimer: {d["context"]}'))

    def seed_ethics_rules(self):
        rules = [
            {'name': 'Block you should', 'rule_type': 'block_phrase', 'pattern': r'\byou should\b', 'severity': 'high'},
            {'name': 'Block you must', 'rule_type': 'block_phrase', 'pattern': r'\byou must\b', 'severity': 'high'},
            {'name': 'Block I recommend', 'rule_type': 'block_phrase', 'pattern': r'\bi recommend\b', 'severity': 'high'},
            {'name': 'Block I advise', 'rule_type': 'block_phrase', 'pattern': r'\bi advise\b', 'severity': 'high'},
            {'name': 'Block file a case', 'rule_type': 'block_phrase', 'pattern': r'\bfile a case\b', 'severity': 'medium'},
            {'name': 'Block hire a lawyer', 'rule_type': 'block_phrase', 'pattern': r'\bhire a lawyer\b', 'severity': 'medium'},
            {'name': 'Block take legal action', 'rule_type': 'block_phrase', 'pattern': r'\btake legal action\b', 'severity': 'medium'},
        ]

        for r in rules:
            obj, created = EthicsRule.objects.update_or_create(
                name=r['name'],
                defaults={**r, 'is_active': True}
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status} rule: {r["name"]}'))