import { useEffect, useState } from 'react';
import { awarenessAPI } from '../services/api';

const EducationPage = () => {
  const [apiContent, setApiContent] = useState([]);

  useEffect(() => {
    awarenessAPI.getEducation()
      .then((res) => setApiContent(res.data.results || []))
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-16 pb-20">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-[#443627]">Legal Awareness & Education</h1>
        <p className="text-lg text-[#725E54] max-w-3xl mx-auto">
          Understand your rights, procedures, and protections in clear and practical language.
        </p>
      </div>

      {apiContent.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-[#443627]">📰 Latest Legal Guides</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {apiContent.map((item) => (
              <div key={item.id} className="bg-white rounded-2xl p-6 shadow border border-[#D5DCF9] hover:shadow-lg transition">
                <span className="text-xs bg-[#D5DCF9] text-[#443627] px-2 py-1 rounded-full font-medium">{item.content_type}</span>
                <h3 className="font-semibold text-[#443627] text-lg mt-3 mb-2">{item.title}</h3>
                <p className="text-sm text-[#725E54]">{item.summary}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-10">
        <SectionCard title="Know Your Fundamental Rights" bg="bg-gradient-to-br from-[#D5DCF9] to-[#A7B0CA]" icon="⚖️">
          <ul className="space-y-2">
            <li><strong>Right to Equality:</strong> Equal protection under law.</li>
            <li><strong>Right to Freedom:</strong> Speech, expression, movement.</li>
            <li><strong>Right Against Exploitation:</strong> Protection from forced labour.</li>
            <li><strong>Right to Constitutional Remedies:</strong> Approach courts if violated.</li>
          </ul>
        </SectionCard>
        <SectionCard title="Rights During Arrest" bg="bg-gradient-to-br from-[#8EDCE6] to-[#A7B0CA]" icon="🚨">
          <ul className="space-y-2">
            <li>Be informed of reason for arrest.</li>
            <li>Right to remain silent.</li>
            <li>Right to consult a lawyer.</li>
            <li>Produced before magistrate within 24 hours.</li>
          </ul>
        </SectionCard>
        <SectionCard title="FIR Filing Process" bg="bg-gradient-to-br from-[#A7B0CA] to-[#D5DCF9]" icon="📄">
          <ol className="space-y-2 list-decimal pl-5">
            <li>Visit nearest police station.</li>
            <li>Explain incident clearly.</li>
            <li>Ensure FIR is read before signing.</li>
            <li>Request free FIR copy.</li>
          </ol>
        </SectionCard>
        <SectionCard title="What is Zero FIR?" bg="bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6]" icon="📍">
          <p>Zero FIR allows filing a complaint at any police station regardless of jurisdiction.</p>
        </SectionCard>
        <SectionCard title="Bail Basics" bg="bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9]" icon="🔓">
          <ul className="space-y-2">
            <li><strong>Bailable:</strong> Bail is a right.</li>
            <li><strong>Non-Bailable:</strong> Court decides.</li>
            <li>Anticipatory bail before arrest.</li>
          </ul>
        </SectionCard>
        <SectionCard title="Protection for Women & Children" bg="bg-gradient-to-br from-[#A7B0CA] to-[#8EDCE6]" icon="🛡️">
          <ul className="space-y-2">
            <li>Female officer mandatory for arrest of women.</li>
            <li>POCSO for child protection.</li>
            <li>Protection against domestic violence.</li>
          </ul>
        </SectionCard>
        <SectionCard title="Key Concepts in BNS / BNSS" bg="bg-gradient-to-br from-[#D5DCF9] to-[#A7B0CA]" icon="📚">
          <ul className="space-y-2">
            <li>Cognizable vs Non-Cognizable</li>
            <li>Compoundable vs Non-Compoundable</li>
            <li>Investigation & Charge Sheet</li>
            <li>Trial & Appeal Structure</li>
          </ul>
        </SectionCard>
        <SectionCard title="Emergency Contacts" bg="bg-gradient-to-br from-[#8EDCE6] to-[#A7B0CA]" icon="📞">
          <ul className="space-y-2">
            <li><strong>Police:</strong> 100</li>
            <li><strong>Women Helpline:</strong> 181</li>
            <li><strong>Child Helpline:</strong> 1098</li>
            <li><strong>National Emergency:</strong> 112</li>
          </ul>
        </SectionCard>
      </div>
    </div>
  );
};

const SectionCard = ({ title, children, bg, icon }) => (
  <div className={`${bg} rounded-3xl p-8 shadow-lg hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 text-[#443627]`}>
    <div className="flex items-center gap-3 mb-4">
      <span className="text-3xl">{icon}</span>
      <h2 className="text-xl font-semibold tracking-wide">{title}</h2>
    </div>
    <div className="text-[#443627]/90 leading-relaxed">{children}</div>
  </div>
);

export default EducationPage;