import React, { useMemo } from 'react';

interface ScientificChartProps {
  currentDeltaG: number;
  currentSw: number;
  currentLogSw: number;
}

const ScientificChart: React.FC<ScientificChartProps> = ({ currentDeltaG, currentSw, currentLogSw }) => {
  // Chart dimensions
  const width = 400;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 50, left: 60 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  // Axes Ranges based on Table 1
  // log10(Sw): X-Axis [0, 4]
  const minLogSw = 0;
  const maxLogSw = 4;
  const logSwRange = maxLogSw - minLogSw;

  // DeltaG: Y-Axis [-25, 15]
  const minDeltaG = -25;
  const maxDeltaG = 15;
  const deltaGRange = maxDeltaG - minDeltaG;

  // Scale Functions
  // X-Axis is log10(Sw)
  const xScale = (val: number) => padding.left + ((val - minLogSw) / logSwRange) * innerWidth;
  // Y-Axis is DeltaG (Inverted Y usually in screen coords, but math is normal Cartesian)
  const yScale = (val: number) => padding.top + innerHeight - ((val - minDeltaG) / deltaGRange) * innerHeight;

  // Reference Data Points from Paper Table 1
  // [logSw, DeltaG, Label]
  const refPoints = [
    { x: 0.70, y: -17.47, label: "4-Cl" },
    { x: 1.30, y: -8.28, label: "1p-Cl" },
    { x: 1.30, y: -8.38, label: "6p-Cl" },
    { x: 1.89, y: -2.56, label: "1p-6p-2Cl" },
    { x: 2.08, y: 0.58, label: "4-1p-2Cl" },
    { x: 1.40, y: -5.83, label: "6-1p-6p-3Cl" },
    { x: 2.80, y: 7.04, label: "4-1p-6p-3Cl" },
    { x: 2.30, y: 10.18, label: "4-6-1p-6p-4Cl" },
    { x: 1.48, y: -5.20, label: "1p-4p-2Cl" },
    { x: 1.40, y: -4.00, label: "1p-4p-6p-3Cl" },
    { x: 2.20, y: 2.05, label: "4-4p-6p-3Cl" },
    { x: 2.34, y: 2.16, label: "4-1p-4p-3Cl" },
    { x: 3.32, y: 8.68, label: "4-1p-4p-6p-4Cl" }
  ];

  // Regression Line: y = 10.13x - 20.72
  const linePoints = useMemo(() => {
    const points = [];
    for (let x = minLogSw; x <= maxLogSw; x += 0.1) {
      const y = 10.13 * x - 20.72;
      // Clamp to view
      if (y >= minDeltaG && y <= maxDeltaG) {
        points.push(`${xScale(x)},${yScale(y)}`);
      }
    }
    return points.join(' ');
  }, []);

  // 95% Confidence Interval
  // Slopes: 8.78 to 11.49
  // Intercepts: -23.44 to -18.01
  // We approximate the area by filling between the two extreme lines
  const confidenceArea = useMemo(() => {
    const pointsTop = [];
    const pointsBottom = [];
    for (let x = minLogSw; x <= maxLogSw; x += 0.1) {
      // Upper bound estimate
      const yHigh = 11.49 * x - 18.01;
      // Lower bound estimate
      const yLow = 8.78 * x - 23.44;
      
      if (yHigh >= minDeltaG && yHigh <= maxDeltaG) pointsTop.push(`${xScale(x)},${yScale(yHigh)}`);
      if (yLow >= minDeltaG && yLow <= maxDeltaG) pointsBottom.unshift(`${xScale(x)},${yScale(yLow)}`);
    }
    return pointsTop.join(' ') + ' ' + pointsBottom.join(' ');
  }, []);

  return (
    <div className="flex flex-col gap-6">
        {/* Regression Chart */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm relative">
            <h3 className="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                Correlation Analysis (Table 1 Data)
            </h3>
            <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
                {/* Grid Lines & Ticks X */}
                {[0, 1, 2, 3, 4].map((tick) => (
                    <g key={tick}>
                        <line 
                            x1={xScale(tick)} y1={padding.top} 
                            x2={xScale(tick)} y2={height - padding.bottom} 
                            stroke="#e2e8f0" strokeDasharray="4 4" 
                        />
                        <text x={xScale(tick)} y={height - 15} textAnchor="middle" fontSize="10" fill="#64748b">
                            {tick}
                        </text>
                    </g>
                ))}
                
                {/* Grid Lines & Ticks Y */}
                {[-20, -10, 0, 10].map((tick) => (
                    <g key={tick}>
                        <line 
                            x1={padding.left} y1={yScale(tick)} 
                            x2={width - padding.right} y2={yScale(tick)} 
                            stroke="#e2e8f0" strokeDasharray="4 4" 
                        />
                        <text x={padding.left - 10} y={yScale(tick) + 3} textAnchor="end" fontSize="10" fill="#64748b">
                            {tick}
                        </text>
                    </g>
                ))}

                {/* Axes Labels */}
                <text x={width / 2} y={height - 5} textAnchor="middle" fontSize="11" fontWeight="bold" fill="#334155">
                    log₁₀(Relative Sweetness)
                </text>
                <text 
                    x={15} y={height / 2} 
                    textAnchor="middle" 
                    fontSize="11" 
                    fontWeight="bold" 
                    fill="#334155" 
                    transform={`rotate(-90, 15, ${height / 2})`}
                >
                    Binding Free Energy (ΔΔG)
                </text>

                {/* Confidence Interval */}
                <polygon points={confidenceArea} fill="#3b82f6" fillOpacity="0.1" />

                {/* Regression Line */}
                <polyline points={linePoints} fill="none" stroke="#3b82f6" strokeWidth="2" />

                {/* Reference Points (Scatter) */}
                {refPoints.map((pt, i) => (
                    <g key={i}>
                        <circle 
                            cx={xScale(pt.x)} 
                            cy={yScale(pt.y)} 
                            r="3" 
                            fill="#64748b" 
                            opacity="0.6"
                        />
                        {/* Tooltip-like label on hover could go here, for now static hidden or tiny */}
                    </g>
                ))}

                {/* Current User Point */}
                <circle 
                    cx={xScale(currentLogSw)} 
                    cy={yScale(currentDeltaG)} 
                    r="6" 
                    fill="#6366f1" 
                    stroke="white" 
                    strokeWidth="2" 
                    className="drop-shadow-md transition-all duration-300"
                />
                
            </svg>
        </div>

        {/* Bar Chart: Comparison */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                Sweetness Multiplier vs Sucrose
            </h3>
            <div className="w-full flex flex-col gap-3">
                {/* Current Compound */}
                <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-600">
                        <span>Current Molecule</span>
                        <span className="text-indigo-600">{currentSw > 1000 ? (currentSw/1000).toFixed(1) + 'k' : currentSw.toFixed(0)}x</span>
                    </div>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
                            style={{ width: `${Math.min(100, (Math.log10(currentSw) / 4) * 100)}%` }}
                        ></div>
                    </div>
                </div>

                {/* Reference: High Sweetness (Table 1 Max) */}
                <div className="space-y-1 opacity-60">
                    <div className="flex justify-between text-xs font-medium text-slate-500">
                        <span>4-1p-4p-6p-4Cl (Ref)</span>
                        <span>~2100x</span>
                    </div>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-blue-400"
                            style={{ width: `${(3.32 / 4) * 100}%` }}
                        ></div>
                    </div>
                </div>

                {/* Reference: Low Sweetness (Table 1 Min) */}
                <div className="space-y-1 opacity-60">
                    <div className="flex justify-between text-xs font-medium text-slate-500">
                        <span>4-Cl-sucrose (Ref)</span>
                        <span>5x</span>
                    </div>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-slate-400"
                            style={{ width: `${(0.70 / 4) * 100}%` }} 
                        ></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
  );
};

export default ScientificChart;
