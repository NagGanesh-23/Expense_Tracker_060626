// dataIngestion.ts
export interface RawTransaction {
  transaction_date: string;
  value_date: string;
  description: string;
  raw_description: string;
  amount: string;
  transaction_type: string;
  balance: string;
  source_account: string;
  month: string;
  year: string;
  transaction_id: string;
  category: string;
  confidence: string;
  classification_method: string;
  review_status: string;
  reviewed_category: string;
  reviewed_at: string;
  reviewer_notes: string;
  ref_no: string;
}

export interface DashboardData {
  totalSpend: number;
  spendChangePct: number;
  chartData: { name: string; current: number; previous: number }[];
  categoryBreakdown: { name: string; value: number; color: string }[];
  breakdownItems: any[];
}

const COLORS = [
  '#1E3A8A', // brand-blue
  '#3B82F6', // brand-slate
  '#93C5FD', // brand-light
  '#DBEAFE', // very light blue
  '#9CA3AF', // gray
  '#4B5563', // dark gray
];

export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) throw new Error('Failed to fetch data');
    const { transactions } = await res.json();
    
    // Process transactions array (assuming first row is header)
    if (!transactions || transactions.length < 2) {
        return getMockData();
    }
    
    const headers = transactions[0];
    const data: RawTransaction[] = transactions.slice(1).map((row: any[]) => {
      const obj: any = {};
      headers.forEach((header: string, index: number) => {
        obj[header] = row[index];
      });
      return obj;
    });

    const debits = data.filter(t => t.transaction_type?.toLowerCase() === 'debit');
    
    // Very simple aggregation for demonstration
    const totalSpend = debits.reduce((sum, t) => sum + parseFloat(t.amount || '0'), 0);
    
    // Group by Category
    const categoryMap = new Map<string, number>();
    debits.forEach(t => {
      const cat = t.category || 'Uncategorized';
      categoryMap.set(cat, (categoryMap.get(cat) || 0) + parseFloat(t.amount || '0'));
    });
    
    const sortedCategories = Array.from(categoryMap.entries())
      .sort((a, b) => b[1] - a[1]);
      
    const categoryBreakdown = sortedCategories.slice(0, 6).map((c, i) => ({
      name: c[0],
      value: c[1],
      color: COLORS[i % COLORS.length]
    }));

    // Mocking chart data based on overall spend (since real dates require complex grouping)
    const chartData = Array.from({length: 6}, (_, i) => ({
      name: `Day ${i*5 + 1}-${i*5 + 5}`,
      current: Math.round(totalSpend / 6 * (0.8 + Math.random() * 0.4)),
      previous: Math.round(totalSpend / 6 * (0.7 + Math.random() * 0.4))
    }));
    
    // Breakdown items (Top 3 categories)
    const breakdownItems = sortedCategories.slice(0, 3).map((c, i) => ({
      id: c[0],
      name: c[0],
      color: COLORS[i],
      amount: c[1] * 0.15, // Mock savings
      savingsRate: Math.round(60 + Math.random() * 30),
      currentValue: c[1] * 0.3,
      targetValue: c[1] * 0.1,
      optimizedCost: Math.round(20 + Math.random() * 20),
    }));

    return {
      totalSpend,
      spendChangePct: 12, // Mock vs last month
      chartData,
      categoryBreakdown,
      breakdownItems
    };
  } catch (err) {
    console.error(err);
    return getMockData();
  }
}

function getMockData(): DashboardData {
  return {
    totalSpend: 8245,
    spendChangePct: 12,
    chartData: [
      { name: '01-05', current: 1200, previous: 900 },
      { name: '06-10', current: 2400, previous: 1500 },
      { name: '11-15', current: 3500, previous: 3200 },
      { name: '16-20', current: 3100, previous: 2800 },
      { name: '21-25', current: 1800, previous: 1600 },
      { name: '26-31', current: 2500, previous: 1900 },
    ],
    categoryBreakdown: [
      { name: 'Food & Dining', value: 3000, color: '#1E3A8A' },
      { name: 'Shopping', value: 2000, color: '#3B82F6' },
      { name: 'Travel', value: 1500, color: '#93C5FD' },
      { name: 'Groceries', value: 1000, color: '#DBEAFE' },
      { name: 'Utilities', value: 745, color: '#9CA3AF' },
    ],
    breakdownItems: [
      {
        id: '1',
        name: 'Food & Dining',
        color: '#3B82F6',
        amount: 1240.0,
        savingsRate: 60,
        currentValue: 200.0,
        targetValue: 60.0,
        optimizedCost: 30,
      },
      {
        id: '2',
        name: 'Shopping',
        color: '#EAB308',
        amount: 2792.7,
        savingsRate: 87,
        currentValue: 240.0,
        targetValue: 96.0,
        optimizedCost: 40,
      },
      {
        id: '3',
        name: 'Travel',
        color: '#F97316',
        amount: 915.0,
        savingsRate: 95,
        currentValue: 120.0,
        targetValue: 24.0,
        optimizedCost: 20,
      },
    ]
  };
}
