import React from 'react';
import { Check, X, AlertCircle } from 'lucide-react';

interface LipinskiBadgeProps {
  mw: number;
  logp: number;
  hbondDonor: number;
  hbondAcceptor: number;
}

const LipinskiBadge: React.FC<LipinskiBadgeProps> = ({ mw, logp, hbondDonor, hbondAcceptor }) => {
  // Lipinski's Rule of 5:
  // 1. MW <= 500
  // 2. LogP <= 5
  // 3. H-bond donors <= 5
  // 4. H-bond acceptors <= 10
  
  const violations = [
    { name: 'MW > 500', passed: mw <= 500 },
    { name: 'LogP > 5', passed: logp <= 5 },
    { name: 'H-Donors > 5', passed: hbondDonor <= 5 },
    { name: 'H-Acceptors > 10', passed: hbondAcceptor <= 10 },
  ];

  const failedCount = violations.filter(v => !v.passed).length;
  const isPass = failedCount <= 1; // Usually 1 violation is allowed

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700">Lipinski Rule of 5</h4>
        <span className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full ${
          isPass ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
        }`}>
          {isPass ? <Check size={12} /> : <X size={12} />}
          {isPass ? 'PASSED' : 'FAILED'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {violations.map((rule) => (
          <div key={rule.name} className={`flex items-center gap-2 text-xs p-2 rounded border ${
            rule.passed ? 'bg-slate-50 border-slate-100 text-slate-600' : 'bg-rose-50 border-rose-100 text-rose-600'
          }`}>
            {rule.passed ? (
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            ) : (
              <AlertCircle size={12} />
            )}
            <span className={rule.passed ? 'opacity-80' : 'font-medium'}>
              {rule.passed ? rule.name.replace('>', '≤') : rule.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LipinskiBadge;
