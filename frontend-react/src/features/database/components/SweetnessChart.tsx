import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface SweetnessChartProps {
  value: number;
  name: string;
}

const SweetnessChart: React.FC<SweetnessChartProps> = ({ value, name }) => {
  // Validate value
  const validValue = isNaN(Number(value)) ? 0 : Number(value);
  
  const data = [
    { name: 'Sucrose', value: 1, type: 'Reference' },
    { name: name || 'Unknown', value: validValue, type: 'Target' },
  ];

  // Determine if we should use log scale visually or just linear with breaks
  const isHighPotency = validValue > 100;
  
  // Use log scale if difference is large (e.g. > 10x)
  const useLogScale = validValue > 10 || validValue < 0.1;

  return (
    <div className="h-full w-full flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-semibold text-slate-700">Relative Sweetness</h4>
        <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
          vs. Sucrose (1.0)
        </span>
      </div>
      
      <div className="flex-1 min-h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            key={`chart-${name}-${validValue}`} // Force re-render on data change
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
            <XAxis 
                type="number" 
                hide 
                scale={useLogScale ? "log" : "linear"} 
                domain={useLogScale ? [0.1, 'auto'] : [0, 'auto']}
                allowDataOverflow={true}
            />
            <YAxis 
              dataKey="name" 
              type="category" 
              width={80} 
              tick={{ fontSize: 12, fill: '#64748b' }} 
              axisLine={false}
              tickLine={false}
            />
            <Tooltip 
              cursor={{ fill: '#f8fafc' }}
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              formatter={(val: any) => [val + 'x', 'Sweetness']}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24} minPointSize={5}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.type === 'Reference' ? '#cbd5e1' : '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-2 flex items-center justify-between px-2">
        <div className="text-xs text-slate-500">
          Potency: <span className="font-bold text-slate-800">{validValue}x</span>
        </div>
        {isHighPotency && (
          <span className="text-[10px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
            High Potency
          </span>
        )}
      </div>
    </div>
  );
};

export default SweetnessChart;
