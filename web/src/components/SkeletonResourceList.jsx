/**
 * SkeletonResourceList Component
 *
 * Shows skeleton loading cards while resources are being fetched.
 */

import './SkeletonResourceList.css';

export default function SkeletonResourceList() {
  return (
    <div className="skeleton-results-card">
      <div className="skeleton-header">
        <div className="skeleton-title"></div>
        <div className="skeleton-subtitle"></div>
      </div>
      
      <div className="skeleton-resources-list">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-resource-item">
            <div className="skeleton-badge"></div>
            <div className="skeleton-resource-title"></div>
            <div className="skeleton-resource-url"></div>
            <div className="skeleton-resource-meta"></div>
          </div>
        ))}
      </div>
    </div>
  );
}

