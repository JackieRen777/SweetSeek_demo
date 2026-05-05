import React from 'react';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip } from 'recharts';

interface PropertyRadarProps {
  data: {
    logp: number;
    tpsa: number;
    mw: number;
    qed: number;
    sa_score: number;
  };
}

const PropertyRadar: React.FC<PropertyRadarProps> = ({ data }) => {
  // Normalize data for radar chart (0-100 scale approximation for visualization)
  // This is a rough normalization for visual comparison
  const chartData = [
    { subject: 'LogP', A: Math.min(Math.max((data.logp + 2) * 20, 0), 100), fullMark: 100, value: data.logp },
    { subject: 'TPSA', A: Math.min(data.tpsa / 2, 100), fullMark: 100, value: data.tpsa },
    { subject: 'MW', A: Math.min(data.mw / 10, 100), fullMark: 100, value: data.mw },
    { subject: 'QED', A: (data.qed || 0) * 100, fullMark: 100, value: data.qed },
    { subject: 'SA Score', A: (data.sa_score || 0) * 10, fullMark: 100, value: data.sa_score },
  ];

  return (
    <div className="h-full w-full flex flex-col items-center">
      <h4 className="text-sm font-semibold text-slate-700 mb-2 w-full text-left">Molecular Property Profile</h4>
      <div className="flex-1 w-full min-h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              name="Properties"
              dataKey="A"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="#8b5cf6"
              fillOpacity={0.2}
            />
            <Tooltip 
              formatter={(_value, _name, props) => [props.payload.value, props.payload.subject]}
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PropertyRadar;
