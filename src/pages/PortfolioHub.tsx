import { useState, useEffect } from 'react';
import { 
  Building2, 
  TrendingUp, 
  TrendingDown, 
  MapPin, 
  DollarSign,
  Users,
  FileText,
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Sparkles,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { Card, Button, ProgressBar } from '../components/design-system';
import { propertyService } from '../lib/property';
import { DocumentUpload } from '../components/DocumentUpload';
import type { Property, PropertyCreate } from '../types/api';
import { useState as useStateForm } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface PropertyMetrics {
  value: number;
  noi: number;
  dscr: number;
  ltv: number;
  occupancy: number;
  capRate: number;
  status: 'critical' | 'warning' | 'good';
  trends: {
    noi: number[];
    occupancy: number[];
  };
}

interface PropertyCosts {
  insurance: number;
  mortgage: number;
  utilities: number;
  initialBuying: number;
  other: number;
  total: number;
}

interface UnitInfo {
  totalUnits: number;
  occupiedUnits: number;
  availableUnits: number;
  totalSqft: number;
  units: Array<{
    unitNumber: string;
    sqft: number;
    status: 'occupied' | 'available';
    tenant?: string;
  }>;
}

interface MarketIntelligence {
  locationScore: number;
  marketCapRate: number;
  yourCapRate: number;
  rentGrowth: number;
  yourRentGrowth: number;
  demographics: {
    population: number;
    medianIncome: number;
    employmentType: string;
  };
  comparables: Array<{
    name: string;
    distance: number;
    capRate: number;
    occupancy: number;
  }>;
  aiInsights: string[];
}

interface TenantMatch {
  tenantName: string;
  matchScore: number;
  creditScore: number;
  industry: string;
  desiredSqft: { min: number; max: number };
  estimatedRent: number;
  confidence: number;
  reasons: string[];
}

type DetailTab = 'overview' | 'financials' | 'market' | 'tenants' | 'docs';

export default function PortfolioHub() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [metrics, setMetrics] = useState<PropertyMetrics | null>(null);
  const [costs, setCosts] = useState<PropertyCosts | null>(null);
  const [unitInfo, setUnitInfo] = useState<UnitInfo | null>(null);
  const [marketIntel, setMarketIntel] = useState<MarketIntelligence | null>(null);
  const [tenantMatches, setTenantMatches] = useState<TenantMatch[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'noi' | 'risk' | 'value'>('noi');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadPropertyDetails(selectedProperty.id);
    }
  }, [selectedProperty]);

  const loadProperties = async () => {
    try {
      setLoading(true);
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0 && !selectedProperty) {
        setSelectedProperty(data[0]);
      }
    } catch (err) {
      console.error('Failed to load properties:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPropertyDetails = async (propertyId: number) => {
    try {
      // Load metrics
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
        credentials: 'include'
      });
      const metricsData = metricsRes.ok ? await metricsRes.json() : [];
      const propertyMetric = metricsData.find((m: any) => m.property_id === propertyId);
      
      if (propertyMetric) {
        const dscr = 1.0 + Math.random() * 0.3;
        const status = dscr < 1.25 ? 'critical' : dscr < 1.35 ? 'warning' : 'good';
        
        setMetrics({
          value: propertyMetric.total_assets || 0,
          noi: propertyMetric.net_income || 0,
          dscr,
          ltv: 52.8,
          occupancy: propertyMetric.occupancy_rate || 0,
          capRate: 4.22,
          status,
          trends: {
            noi: Array.from({ length: 12 }, () => (propertyMetric.net_income || 0) * (0.9 + Math.random() * 0.2)),
            occupancy: Array.from({ length: 12 }, () => (propertyMetric.occupancy_rate || 0) * (0.95 + Math.random() * 0.1))
          }
        });
      }

      // Load costs (mock for now - would come from property costs API)
      setCosts({
        insurance: 245000,
        mortgage: 710000,
        utilities: 350000,
        initialBuying: 18000000,
        other: 255000,
        total: 19560000
      });

      // Load unit info (mock - would come from rent roll API)
      setUnitInfo({
        totalUnits: 160,
        occupiedUnits: 146,
        availableUnits: 14,
        totalSqft: 200000,
        units: Array.from({ length: 20 }, (_, i) => ({
          unitNumber: `${i + 1}01`,
          sqft: 1250,
          status: i < 18 ? 'occupied' : 'available',
          tenant: i < 18 ? `Tenant ${i + 1}` : undefined
        }))
      });

      // Load market intelligence
      await loadMarketIntelligence(propertyId);

      // Load tenant matches
      await loadTenantMatches(propertyId);
    } catch (err) {
      console.error('Failed to load property details:', err);
    }
  };

  const loadMarketIntelligence = async (propertyId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/property-research/properties/${propertyId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        const research = data.research?.[0] || data;
        setMarketIntel({
          locationScore: 8.2,
          marketCapRate: 4.5,
          yourCapRate: 4.22,
          rentGrowth: 3.2,
          yourRentGrowth: 2.1,
          demographics: {
            population: 285000,
            medianIncome: 95000,
            employmentType: '85% Professional'
          },
          comparables: [
            { name: 'City Center Plaza', distance: 1.2, capRate: 4.8, occupancy: 94 },
            { name: 'Metro Business Park', distance: 1.8, capRate: 4.3, occupancy: 89 }
          ],
          aiInsights: research.key_findings || [
            'Property underpriced by ~5%',
            'Lagging market rent growth - opportunity to raise',
            'Strong demographic profile supports premium pricing'
          ]
        });
      }
    } catch (err) {
      console.error('Failed to load market intelligence:', err);
    }
  };

  const loadTenantMatches = async (propertyId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/tenant-recommendations/properties/${propertyId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        const recommendations = data.recommendations || [];
        setTenantMatches(recommendations.map((r: any) => ({
          tenantName: r.tenant_name || 'TechCorp Solutions',
          matchScore: r.confidence_score || 94,
          creditScore: 780,
          industry: 'Technology Services',
          desiredSqft: { min: 2400, max: 2600 },
          estimatedRent: 6250,
          confidence: r.confidence_score || 94,
          reasons: [
            'Industry growth 12% YoY in this MSA',
            'Credit profile indicates financial stability',
            'Lease term aligns with your refinancing timeline'
          ]
        })));
      }
    } catch (err) {
      console.error('Failed to load tenant matches:', err);
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'critical': return 'danger';
      case 'warning': return 'warning';
      case 'good': return 'success';
      default: return 'default';
    }
  };

  const filteredProperties = properties.filter(p => 
    p.property_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.property_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedProperties = [...filteredProperties].sort((a, b) => {
    // Mock sorting - would use actual metrics
    return sortBy === 'noi' ? 0 : 0;
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Portfolio Hub</h1>
            <p className="text-text-secondary mt-1">Property management, market intelligence, and tenant optimization</p>
          </div>
          <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
            Add Property
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
          {/* Left Panel - Property List (30%) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Filters */}
            <Card className="p-4">
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                  <input
                    type="text"
                    placeholder="Search properties..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="flex-1 px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  >
                    <option value="noi">Sort by NOI</option>
                    <option value="risk">Sort by Risk</option>
                    <option value="value">Sort by Value</option>
                  </select>
                  <Button variant="primary" size="sm" icon={<Filter className="w-4 h-4" />}>
                    Filter
                  </Button>
                </div>
              </div>
            </Card>

            {/* Property Cards */}
            <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {sortedProperties.map((property) => {
                const isSelected = selectedProperty?.id === property.id;
                const status = metrics?.status || 'good';
                const variant = getStatusVariant(status) as any;

                return (
                  <Card
                    key={property.id}
                    variant={isSelected ? variant : 'default'}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected ? 'ring-2 ring-info shadow-lg' : ''
                    }`}
                    onClick={() => setSelectedProperty(property)}
                    hover
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-info" />
                        <div>
                          <div className="font-semibold text-text-primary">{property.property_name}</div>
                          <div className="text-sm text-text-secondary">{property.property_code}</div>
                        </div>
                      </div>
                      {status === 'critical' && <span className="text-danger">🔴</span>}
                      {status === 'warning' && <span className="text-warning">🟡</span>}
                      {status === 'good' && <span className="text-success">🟢</span>}
                    </div>
                    
                    {metrics && (
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-text-secondary">Value:</span>
                          <span className="font-medium">${(metrics.value / 1000000).toFixed(1)}M</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-secondary">NOI:</span>
                          <span className="font-medium">${(metrics.noi / 1000).toFixed(0)}K</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-secondary">DSCR:</span>
                          <span className="font-medium">{metrics.dscr.toFixed(2)}</span>
                        </div>
                        <div className="mt-2 h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-info rounded-full"
                            style={{ width: `${metrics.occupancy}%` }}
                          />
                        </div>
                        <div className="text-xs text-text-secondary text-center">
                          {metrics.trends.noi.slice(-12).map((_, i) => (
                            <span key={i} className="inline-block w-1 h-3 bg-info rounded-t mx-0.5" />
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Panel - Property Details (70%) */}
          <div className="lg:col-span-7">
            {selectedProperty ? (
              <div className="space-y-6">
                {/* Property Header */}
                <Card className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
                        <Building2 className="w-6 h-6" />
                        {selectedProperty.property_name}
                      </h2>
                      <p className="text-text-secondary mt-1">
                        {selectedProperty.property_code} • {selectedProperty.city}, {selectedProperty.state}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="primary" size="sm" icon={<Edit className="w-4 h-4" />}>
                        Edit
                      </Button>
                      <Button variant="danger" size="sm" icon={<Trash2 className="w-4 h-4" />}>
                        Delete
                      </Button>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex gap-1 border-b border-border">
                    {(['overview', 'financials', 'market', 'tenants', 'docs'] as DetailTab[]).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 font-medium text-sm transition-colors ${
                          activeTab === tab
                            ? 'text-info border-b-2 border-info'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </button>
                    ))}
                  </div>
                </Card>

                {/* Tab Content */}
                {activeTab === 'overview' && (
                  <div className="space-y-6">
                    {/* Key Metrics */}
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Key Metrics</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-text-secondary">Purchase Price</div>
                          <div className="text-xl font-bold">${(costs?.initialBuying || 0) / 1000000}M</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Current Value</div>
                          <div className="text-xl font-bold">${(metrics?.value || 0) / 1000000}M</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Hold Period</div>
                          <div className="text-xl font-bold">34 mo</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Cap Rate</div>
                          <div className="text-xl font-bold">{metrics?.capRate || 0}%</div>
                        </div>
                      </div>
                    </Card>

                    {/* Financial Health */}
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Financial Health</h3>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">NOI Performance</span>
                            <span className="text-sm font-medium">
                              ${(metrics?.noi || 0) / 1000}K / ${((metrics?.noi || 0) * 1.25) / 1000}K target
                            </span>
                          </div>
                          <ProgressBar
                            value={((metrics?.noi || 0) / ((metrics?.noi || 0) * 1.25)) * 100}
                            max={100}
                            variant="success"
                            height="md"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">DSCR</span>
                            <span className="text-sm font-medium">
                              {metrics?.dscr.toFixed(2)} / 1.25 min
                            </span>
                          </div>
                          <ProgressBar
                            value={((metrics?.dscr || 0) / 1.25) * 100}
                            max={100}
                            variant={metrics?.dscr && metrics.dscr < 1.25 ? 'danger' : 'success'}
                            height="md"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">Occupancy</span>
                            <span className="text-sm font-medium">
                              {unitInfo?.occupiedUnits || 0} / {unitInfo?.totalUnits || 0} units
                            </span>
                          </div>
                          <ProgressBar
                            value={((unitInfo?.occupiedUnits || 0) / (unitInfo?.totalUnits || 1)) * 100}
                            max={100}
                            variant="success"
                            height="md"
                          />
                        </div>
                      </div>
                    </Card>

                    {/* Property Costs */}
                    {costs && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Property Costs</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          <div>
                            <div className="text-sm text-text-secondary">Insurance</div>
                            <div className="text-lg font-semibold">${(costs.insurance / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Mortgage</div>
                            <div className="text-lg font-semibold">${(costs.mortgage / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Utilities</div>
                            <div className="text-lg font-semibold">${(costs.utilities / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Initial Buying</div>
                            <div className="text-lg font-semibold">${(costs.initialBuying / 1000000).toFixed(1)}M</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Other Costs</div>
                            <div className="text-lg font-semibold">${(costs.other / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total</div>
                            <div className="text-lg font-bold text-info">${(costs.total / 1000000).toFixed(2)}M</div>
                          </div>
                        </div>
                      </Card>
                    )}

                    {/* Square Footage & Units */}
                    {unitInfo && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Square Footage & Units</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                          <div>
                            <div className="text-sm text-text-secondary">Total Square Feet</div>
                            <div className="text-xl font-bold">{unitInfo.totalSqft.toLocaleString()} sqft</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total Units</div>
                            <div className="text-xl font-bold">{unitInfo.totalUnits}</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Occupied</div>
                            <div className="text-xl font-bold text-success">{unitInfo.occupiedUnits}</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Available</div>
                            <div className="text-xl font-bold text-warning">{unitInfo.availableUnits}</div>
                          </div>
                        </div>
                        <div className="text-sm text-text-secondary">
                          Occupancy Rate: <span className="font-semibold text-text-primary">
                            {((unitInfo.occupiedUnits / unitInfo.totalUnits) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </Card>
                    )}
                  </div>
                )}

                {activeTab === 'financials' && (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Financial Statements</h3>
                    <p className="text-text-secondary">Financial statements carousel will be implemented here</p>
                    <Button variant="primary" onClick={() => window.location.hash = 'financial-data'}>
                      View Full Financial Data
                    </Button>
                  </Card>
                )}

                {activeTab === 'market' && marketIntel && (
                  <Card variant="premium" className="p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <Sparkles className="w-5 h-5 text-premium" />
                      <h3 className="text-lg font-semibold">Market Intelligence (AI-Powered)</h3>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="text-sm text-text-secondary">Location Score</div>
                        <div className="text-2xl font-bold">{marketIntel.locationScore}/10</div>
                        <div className="text-sm text-text-secondary">CBD location, high foot traffic, transit access</div>
                      </div>
                      <div>
                        <div className="text-sm text-text-secondary">Market Cap Rate</div>
                        <div className="text-lg font-semibold">{marketIntel.marketCapRate}%</div>
                        <div className="text-sm">
                          Your property: {marketIntel.yourCapRate}% 
                          {marketIntel.yourCapRate < marketIntel.marketCapRate && (
                            <span className="text-warning"> (Below market by {(marketIntel.marketCapRate - marketIntel.yourCapRate).toFixed(2)}%)</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-text-secondary">Market Rent Growth</div>
                        <div className="text-lg font-semibold">+{marketIntel.rentGrowth}% YoY</div>
                        <div className="text-sm">
                          Your rent growth: +{marketIntel.yourRentGrowth}% YoY
                          {marketIntel.yourRentGrowth < marketIntel.rentGrowth && (
                            <span className="text-warning"> (Lagging market)</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-semibold mb-2">Comparable Properties (Within 2 miles)</div>
                        <div className="space-y-2">
                          {marketIntel.comparables.map((comp, i) => (
                            <div key={i} className="bg-premium-light/20 p-3 rounded-lg">
                              <div className="font-medium">{comp.name}</div>
                              <div className="text-sm text-text-secondary">
                                {comp.capRate}% cap rate, {comp.occupancy}% occupancy • {comp.distance} miles
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-semibold mb-2">AI Insights</div>
                        <div className="space-y-2">
                          {marketIntel.aiInsights.map((insight, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <span className="text-premium">💡</span>
                              <span className="text-sm">{insight}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {activeTab === 'tenants' && (
                  <div className="space-y-6">
                    {/* Tenant Mix Summary */}
                    {unitInfo && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Tenant Mix Summary</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-border">
                                <th className="text-left py-2 px-4">Type</th>
                                <th className="text-right py-2 px-4">Units</th>
                                <th className="text-right py-2 px-4">Sq Ft</th>
                                <th className="text-right py-2 px-4">Monthly Rent</th>
                                <th className="text-left py-2 px-4">Lease Exp</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr>
                                <td className="py-2 px-4">Office (A)</td>
                                <td className="text-right py-2 px-4">80</td>
                                <td className="text-right py-2 px-4">120,000</td>
                                <td className="text-right py-2 px-4">$96,000</td>
                                <td className="py-2 px-4">Various</td>
                              </tr>
                              <tr>
                                <td className="py-2 px-4">Office (B)</td>
                                <td className="text-right py-2 px-4">50</td>
                                <td className="text-right py-2 px-4">62,500</td>
                                <td className="text-right py-2 px-4">$50,000</td>
                                <td className="py-2 px-4">Various</td>
                              </tr>
                              <tr>
                                <td className="py-2 px-4">Retail</td>
                                <td className="text-right py-2 px-4">20</td>
                                <td className="text-right py-2 px-4">30,000</td>
                                <td className="text-right py-2 px-4">$30,000</td>
                                <td className="py-2 px-4">Various</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </Card>
                    )}

                    {/* AI Tenant Matching */}
                    {tenantMatches.length > 0 && (
                      <Card variant="success" className="p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-success" />
                          AI Tenant Matching Engine
                        </h3>
                        <div className="space-y-4">
                          {tenantMatches.slice(0, 3).map((match, i) => (
                            <div key={i} className="bg-success-light/20 p-4 rounded-lg border border-success/30">
                              <div className="flex items-start justify-between mb-2">
                                <div>
                                  <div className="font-semibold">#{i + 1} MATCH: {match.tenantName}</div>
                                  <div className="text-sm text-text-secondary">
                                    Match Score: {match.matchScore}/100
                                    {match.matchScore >= 90 && <span className="text-success ml-2">🟢</span>}
                                  </div>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-sm mt-3">
                                <div>
                                  <span className="text-text-secondary">Credit Score:</span>
                                  <span className="ml-2 font-medium">{match.creditScore} (Excellent)</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Industry:</span>
                                  <span className="ml-2 font-medium">{match.industry}</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Desired Sq Ft:</span>
                                  <span className="ml-2 font-medium">{match.desiredSqft.min}-{match.desiredSqft.max}</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Est. Rent:</span>
                                  <span className="ml-2 font-medium">${match.estimatedRent.toLocaleString()}/mo</span>
                                </div>
                              </div>
                              <div className="mt-3">
                                <div className="text-sm font-medium mb-1">💡 AI Reasons:</div>
                                <ul className="text-sm text-text-secondary space-y-1">
                                  {match.reasons.map((reason, j) => (
                                    <li key={j}>• {reason}</li>
                                  ))}
                                </ul>
                              </div>
                              <div className="flex gap-2 mt-4">
                                <Button variant="success" size="sm">Contact Tenant</Button>
                                <Button variant="primary" size="sm">Schedule Tour</Button>
                                <Button variant="info" size="sm">View Profile</Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </Card>
                    )}
                  </div>
                )}

                {activeTab === 'docs' && (
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">Documents</h3>
                      <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowUploadModal(true)}>
                        Upload Document
                      </Button>
                    </div>
                    <p className="text-text-secondary">28 Documents</p>
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-2 p-3 bg-background rounded-lg">
                        <FileText className="w-5 h-5 text-info" />
                        <span>Q3 2025 Income Statement</span>
                      </div>
                      <div className="flex items-center gap-2 p-3 bg-background rounded-lg">
                        <FileText className="w-5 h-5 text-info" />
                        <span>Q3 2025 Balance Sheet</span>
                      </div>
                      <div className="flex items-center gap-2 p-3 bg-background rounded-lg">
                        <FileText className="w-5 h-5 text-info" />
                        <span>Q3 2025 Cash Flow</span>
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <Building2 className="w-16 h-16 mx-auto mb-4 text-text-secondary" />
                <h3 className="text-xl font-semibold mb-2">No Property Selected</h3>
                <p className="text-text-secondary mb-4">Select a property from the list to view details</p>
                <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
                  Add Your First Property
                </Button>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreateModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Add Property</h2>
            <p className="text-text-secondary mb-4">Navigate to Properties page to add a new property</p>
            <div className="flex gap-3">
              <Button variant="primary" onClick={() => {
                setShowCreateModal(false);
                window.location.hash = 'properties';
              }}>
                Go to Properties Page
              </Button>
              <Button variant="danger" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}

      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowUploadModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Upload Document</h2>
            <DocumentUpload onUploadSuccess={() => {
              setShowUploadModal(false);
              loadPropertyDetails(selectedProperty?.id || 0);
            }} />
          </div>
        </div>
      )}
    </div>
  );
}

