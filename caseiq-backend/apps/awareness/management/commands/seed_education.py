from django.core.management.base import BaseCommand
from apps.awareness.models import EducationalContent


class Command(BaseCommand):
    help = 'Seed educational content'

    def handle(self, *args, **options):
        contents = [
            {
                'title': 'How to File an FIR in India',
                'content_type': 'guide',
                'summary': 'A step-by-step guide to filing a First Information Report (FIR) at a police station in India.',
                'content': '''Filing an FIR (First Information Report) is your legal right as a citizen of India. Under BNSS Section 173, the police are obligated to register your complaint.

STEP 1 — GO TO THE RIGHT POLICE STATION
Visit the police station in whose jurisdiction the crime occurred. If you are unsure, go to the nearest station and they will guide you.

STEP 2 — WHAT TO BRING
Bring any evidence you have — photographs, videos, documents, witness contact details. Also carry your ID proof (Aadhaar card, PAN card etc.)

STEP 3 — GIVE YOUR COMPLAINT
You can give your complaint verbally or in writing. The police officer on duty is required to reduce it to writing. You can also email your complaint to the SP or DCP of the district.

STEP 4 — READ BEFORE SIGNING
The officer will write the FIR and read it back to you. Read it carefully before signing. Ensure all facts are recorded correctly.

STEP 5 — GET YOUR COPY
You are legally entitled to a FREE copy of the FIR under BNSS Section 173(2). Do not leave without a copy. The copy will have an FIR number — note it down.

STEP 6 — IF POLICE REFUSE
If police refuse to register your FIR, you can: (1) Approach the Superintendent of Police, (2) Send complaint by registered post to the Magistrate, (3) File a complaint directly with the Magistrate under BNSS Section 175.

KEY LEGAL PROVISIONS:
- BNSS Section 173 — Mandatory FIR registration for cognizable offences
- BNSS Section 175 — Magistrate can order FIR registration
- Article 21 — Right to life and liberty (Constitutional protection)''',
                'target_audience': 'citizen',
                'language': 'en',
                'tags': ['FIR', 'police complaint', 'BNSS', 'citizen rights'],
                'related_laws': ['BNSS Section 173', 'BNSS Section 175'],
                'is_published': True,
            },
            {
                'title': 'Your Rights When Arrested in India',
                'content_type': 'article',
                'summary': 'Know your fundamental rights at the time of arrest under the Indian Constitution and BNSS.',
                'content': '''If you are arrested in India, you have specific rights that the police MUST respect. These are protected by the Constitution and BNSS.

RIGHT 1 — RIGHT TO KNOW THE GROUNDS OF ARREST
Under Article 22(1) of the Constitution and BNSS Section 47, the police must tell you why you are being arrested. They cannot arrest you without giving a reason.

RIGHT 2 — RIGHT TO INFORM SOMEONE
You have the right to inform a family member, friend, or lawyer about your arrest. Under BNSS Section 50, the police must allow you to do this.

RIGHT 3 — RIGHT TO A LAWYER
Under Article 22(1), you have the right to consult a lawyer of your choice. If you cannot afford one, the state must provide one free of charge under the Legal Services Authorities Act.

RIGHT 4 — RIGHT AGAINST SELF-INCRIMINATION
Under Article 20(3), you cannot be forced to be a witness against yourself. You have the right to remain silent.

RIGHT 5 — RIGHT TO BE PRODUCED BEFORE A MAGISTRATE
Under BNSS Section 57, you must be produced before a Magistrate within 24 hours of arrest. This is a fundamental right.

RIGHT 6 — RIGHT AGAINST ILLEGAL DETENTION
If you are illegally detained, you can file a Habeas Corpus petition in the High Court or Supreme Court.

WHAT TO DO IF YOUR RIGHTS ARE VIOLATED:
- Note down names and badge numbers of officers involved
- Inform family immediately
- Contact a lawyer
- File a complaint with the State Human Rights Commission
- Approach the High Court''',
                'target_audience': 'citizen',
                'language': 'en',
                'tags': ['arrest', 'rights', 'BNSS', 'constitution', 'lawyer'],
                'related_laws': ['Article 22', 'BNSS Section 47', 'BNSS Section 50', 'BNSS Section 57'],
                'is_published': True,
            },
            {
                'title': 'Understanding BNS vs IPC — What Changed?',
                'content_type': 'article',
                'summary': 'A plain language explanation of how the new Bharatiya Nyaya Sanhita (BNS) 2023 replaced the Indian Penal Code (IPC) 1860.',
                'content': '''In 2023, India replaced three colonial-era laws with new legislation. Here is what changed and why it matters to you.

THE THREE NEW LAWS:
1. Bharatiya Nyaya Sanhita (BNS) 2023 — Replaces IPC 1860
2. Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 — Replaces CrPC 1973
3. Bharatiya Sakshya Adhiniyam (BSA) 2023 — Replaces Indian Evidence Act 1872

KEY CHANGES IN BNS:
- Organized crime and terrorism now explicitly defined
- New provisions for crimes against women
- Section numbers changed — important for FIR filings
- Murder (was IPC 302) is now BNS Section 103
- Theft (was IPC 378) is now BNS Section 303
- Rape (was IPC 375) is now BNS Section 63

KEY CHANGES IN BNSS:
- FIR can now be filed online (zero FIR)
- Bail provisions simplified
- Trial timelines mandated (must complete in 3 years)
- Electronic evidence now explicitly covered
- Victim has right to be heard at every stage

WHY DOES THIS MATTER TO YOU:
When filing a complaint or FIR, use the new BNS/BNSS section numbers. Courts are now using the new laws for all offences committed after July 1, 2024.

If your case was registered before July 1, 2024, it will continue under the old IPC/CrPC.''',
                'target_audience': 'citizen',
                'language': 'en',
                'tags': ['BNS', 'IPC', 'BNSS', 'CrPC', 'new law', 'legal reform'],
                'related_laws': ['BNS 2023', 'BNSS 2023', 'BSA 2023'],
                'is_published': True,
            },
            {
                'title': 'Consumer Rights in India — How to File a Complaint',
                'content_type': 'guide',
                'summary': 'A practical guide to understanding your consumer rights and how to file a complaint against defective products or poor services.',
                'content': '''As a consumer in India, you have strong legal protections under the Consumer Protection Act 2019.

YOUR BASIC CONSUMER RIGHTS:
1. Right to Safety — Protection against hazardous products
2. Right to Information — Truthful product information
3. Right to Choose — Access to variety at competitive prices
4. Right to be Heard — Your complaints must be addressed
5. Right to Redressal — Compensation for defective goods/services
6. Right to Consumer Education — Awareness of rights

WHERE TO FILE A COMPLAINT:
- District Commission — Claims up to Rs. 50 lakhs
- State Commission — Claims Rs. 50 lakhs to Rs. 2 crores
- National Commission — Claims above Rs. 2 crores
- Online: consumerhelpline.gov.in or edaakhil.nic.in

WHAT YOU CAN CLAIM:
- Replacement of defective product
- Refund of purchase price
- Compensation for loss or injury
- Removal of deficiency in service
- Discontinuation of unfair trade practices

HOW TO FILE:
1. Send legal notice to seller/company first
2. Collect all receipts, bills, warranty cards
3. File complaint online at edaakhil.nic.in
4. Pay nominal court fee (based on claim amount)
5. Attend hearings or appoint a representative''',
                'target_audience': 'citizen',
                'language': 'en',
                'tags': ['consumer rights', 'complaint', 'consumer court', 'refund'],
                'related_laws': ['Consumer Protection Act 2019'],
                'is_published': True,
            },
        ]

        for item in contents:
            obj, created = EducationalContent.objects.get_or_create(
                title=item['title'],
                defaults=item
            )
            status = 'Created' if created else 'Skipped'
            self.stdout.write(self.style.SUCCESS(f'{status}: {item["title"]}'))

        self.stdout.write(self.style.SUCCESS(f'\nTotal educational content: {EducationalContent.objects.count()}'))