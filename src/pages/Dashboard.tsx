import { useState, useEffect } from 'react';
import { propertyService } from '../lib/property';
import { documentService } from '../lib/document';
import { reviewService } from '../lib/review';
import { MetricCard } from '../components/ui';
import { PortfolioHealthCard } from '../components/widgets/PortfolioHealthCard';
import { CriticalAlertsWidget } from '../components/widgets/CriticalAlertsWidget';
import { 
  Building2, 
  FileText, 
  CheckCircle, 
  Clock, 
  TrendingUp 
} from 'lucide-react';
import type { Property, DocumentUpload } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export default function Dashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [documents, setDocuments] = useState<DocumentUpload[]>([]);
  const [stats, setStats] = useState({
    totalProperties: 0,
    totalDocuments: 0,
    pendingReviews: 0,
    completedExtractions: 0,
  });
  
  // Widget Data
  const [portfolioHealth, setPortfolioHealth] = useState({
    score: null as number | null,
    status: 'loading' as 'excellent' | 'good' | 'fair' | 'poor' | 'loading',
    avgOccupancy: 0,
    criticalAlerts: 0
  });
  const [criticalAlerts, setCriticalAlerts] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [propertiesData, documentsResponse, reviewQueueData] = await Promise.all([
        propertyService.getAllProperties(),
        documentService.getDocuments({ limit: 100 }),
        reviewService.getReviewQueue({ limit: 1000 }).catch(() => ({ items: [], total: 0 }))
      ]);

      setProperties(propertiesData);
      const docs = documentsResponse.items || documentsResponse as any;
      setDocuments(docs.slice(0, 10)); // Recent 10

      // Calculate basic stats
      const reviewItems = reviewQueueData.items || [];
      const totalProps = propertiesData.length;
      
      setStats({
        totalProperties: totalProps,
        totalDocuments: (documentsResponse.total || (documentsResponse as any).length),
        pendingReviews: reviewItems.length,
        completedExtractions: docs.filter((d: DocumentUpload) => d.extraction_status === 'completed').length
      });

      // Load Risk & Health Data
      await loadRiskAndHealthData(totalProps);

    } catch (err) {
      console.error('Failed to load dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  const loadRiskAndHealthData = async (totalProperties: number) => {
    try {
      // 1. Fetch Critical Alerts
      const alertsRes = await fetch(`${API_BASE_URL}/risk-alerts/alerts?severity=CRITICAL&status=ACTIVE&limit=5`, { credentials: 'include' });
      let alertsCount = 0;
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        const items = alertsData.alerts || alertsData;
        
        // Map to widget format
        const mappedAlerts = Array.isArray(items) ? items.map((a: any) => ({
          id: a.id,
          title: a.metric_name || a.alert_type || 'Critical Alert',
          property_name: a.property_name || 'Unknown Property',
          severity: a.severity || 'critical',
          created_at: a.created_at || new Date().toISOString()
        })) : [];
        
        setCriticalAlerts(mappedAlerts);
        alertsCount = mappedAlerts.length;
      }

      // 2. Calculate simplified portfolio health
      // For full calculation we need metrics/summary. 
      // We'll do a simplified fetch or defaulting if plain fetch fails.
      let avgOcc = 0;
      let score = 85; 

      try {
        const summaryRes = await fetch(`${API_BASE_URL}/metrics/summary?year=${new Date().getFullYear() - 1}`, { credentials: 'include' }); // use previous year (2023 usually)
        if (summaryRes.ok) {
           const metrics = await summaryRes.json();
           // simple avg occupancy
           const withOcc = metrics.filter((m: any) => m.occupancy_rate != null);
           if (withOcc.length > 0) {
             const sumOcc = withOcc.reduce((acc: number, curr: any) => acc + curr.occupancy_rate, 0);
             avgOcc = sumOcc / withOcc.length;
           }
        }
      } catch (e) {
        console.warn('Failed to fetch metrics summary', e);
      }

      // Basic Score Logic
      if (avgOcc > 0 && avgOcc < 85) score -= 15;
      if (alertsCount > 0) score -= (alertsCount * 5);
      score = Math.max(0, Math.min(100, score));
      
      const status = score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'poor';

      setPortfolioHealth({
        score,
        status,
        avgOccupancy: avgOcc,
        criticalAlerts: alertsCount,
      });

    } catch (err) {
      console.error('Error loading risk/health data', err);
      setPortfolioHealth(prev => ({ ...prev, status: 'fair' })); // fallback
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'var(--success-color)';
      case 'processing': return 'var(--primary-color)';
      case 'pending': return 'var(--warning-color)';
      case 'failed': return 'var(--error-color)';
      default: return 'var(--secondary-color)';
    }
  };

  if (loading) {
    return (
      <div className="page p-6">
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-3"></div>
          Loading dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-8 max-w-[1600px] mx-auto w-full">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Financial document processing overview</p>
        </div>
        <div className="text-sm text-gray-400">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
      
      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Properties"
          value={stats.totalProperties.toString()}
          icon={<Building2 size={24} className="text-blue-600" />}
          status="info"
          className="bg-white"
        />
        <MetricCard
          title="Documents Processed"
          value={stats.completedExtractions.toString()}
          icon={<CheckCircle size={24} className="text-green-600" />}
          status="success"
          comparison={`${stats.totalDocuments} total uploaded`}
        />
        <MetricCard
          title="Pending Reviews"
          value={stats.pendingReviews.toString()}
          icon={<Clock size={24} className="text-orange-600" />}
          status={stats.pendingReviews > 0 ? "warning" : "success"}
          comparison="Requires attention"
        />
        <MetricCard
          title="Processing Success"
          value={`${stats.totalDocuments > 0 ? Math.round((stats.completedExtractions / stats.totalDocuments) * 100) : 0}%`}
          icon={<TrendingUp size={24} className="text-indigo-600" />}
          status="info"
        />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Health & Risks */}
        <div className="space-y-6">
           <PortfolioHealthCard 
             score={portfolioHealth.score}
             status={portfolioHealth.status}
             totalProperties={stats.totalProperties}
             avgOccupancy={portfolioHealth.avgOccupancy}
             criticalAlerts={portfolioHealth.criticalAlerts}
           />
           
           <CriticalAlertsWidget 
             alerts={criticalAlerts}
             onViewAll={() => window.location.href = '/risk-intelligence'}
           />
        </div>

        {/* Middle/Right Column: Recent Activity & Properties */}
        <div className="lg:col-span-2 space-y-6">
           {/* Recent Uploads */}
           <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
             <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
               <h3 className="font-semibold text-gray-900">Recent Document Uploads</h3>
               <button 
                 onClick={() => window.location.href = '/documents'}
                 className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                 View All
               </button>
             </div>
             {documents.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No documents uploaded yet</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                      <tr>
                        <th className="px-6 py-3 font-medium">File Name</th>
                        <th className="px-6 py-3 font-medium">Type</th>
                        <th className="px-6 py-3 font-medium">Status</th>
                        <th className="px-6 py-3 font-medium">Uploaded</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4 font-medium text-gray-900">{doc.file_name}</td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              {doc.document_type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center">
                               <span 
                                  className="w-2 h-2 rounded-full mr-2"
                                  style={{ backgroundColor: getStatusColor(doc.extraction_status) }}
                                />
                                <span className="capitalize">{doc.extraction_status}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-gray-500">
                            {new Date(doc.upload_date).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
           </div>

           {/* Properties List (Brief) */}
           <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                 <h3 className="font-semibold text-gray-900">Active Properties</h3>
                 <button 
                   onClick={() => window.location.href = '/properties'}
                   className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                 >
                   View All
                 </button>
              </div>
              <div className="p-6">
                 {properties.length === 0 ? (
                    <div className="text-center text-gray-500">No properties found</div>
                 ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                       {properties.slice(0, 6).map((prop) => (
                          <div key={prop.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                             <div className="flex justify-between items-start mb-2">
                                <span className="font-bold text-gray-900">{prop.property_code}</span>
                                <span className={`px-2 py-0.5 rounded text-xs uppercase font-semibold ${
                                   prop.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'
                                }`}>
                                   {prop.status}
                                </span>
                             </div>
                             <div className="text-sm font-medium text-gray-800 truncate" title={prop.property_name}>
                                {prop.property_name}
                             </div>
                             <div className="text-xs text-gray-500 mt-1">
                                {prop.city}, {prop.state}
                             </div>
                          </div>
                       ))}
                    </div>
                 )}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
