import { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Phone, Navigation, AlertCircle } from 'lucide-react';
import PageTransition from '../components/ui/PageTransition';

const NearbyStationsPage = () => {
  const [location, setLocation] = useState(null);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [permissionDenied, setPermissionDenied] = useState(false);

  const getLocation = () => {
    setLoading(true);
    setError('');

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setLocation({ lat: latitude, lng: longitude });
        fetchNearbyStations(latitude, longitude);
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setPermissionDenied(true);
          setError('Location permission denied. Please enable location access.');
        } else {
          setError('Could not get your location. Please try again.');
        }
        setLoading(false);
        loadMockStations();
      },
      { timeout: 10000, maximumAge: 300000 }
    );
  };

  const fetchNearbyStations = async (lat, lng) => {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_KEY;

    if (!apiKey) {
      loadMockStations();
      return;
    }

    try {
      const url = `https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=${lat},${lng}&radius=5000&type=police&key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.results?.length > 0) {
        setStations(data.results.map((place) => ({
          id: place.place_id,
          name: place.name,
          address: place.vicinity,
          distance: getDistance(lat, lng, place.geometry.location.lat, place.geometry.location.lng),
          rating: place.rating,
          open: place.opening_hours?.open_now,
          lat: place.geometry.location.lat,
          lng: place.geometry.location.lng,
          phone: null,
        })));
      } else {
        loadMockStations();
      }
    } catch {
      loadMockStations();
    } finally {
      setLoading(false);
    }
  };

  const loadMockStations = () => {
    setStations([
      { id: 1, name: 'Local Police Station', address: 'Based on your area', distance: '< 2 km', phone: '100', open: true, lat: null, lng: null },
      { id: 2, name: 'District Police Headquarters', address: 'District HQ', distance: '< 5 km', phone: '100', open: true, lat: null, lng: null },
      { id: 3, name: 'Cyber Crime Cell', address: 'Cyber Police Station', distance: 'Varies', phone: '1930', open: true, lat: null, lng: null },
      { id: 4, name: 'Women Police Station', address: 'Women & Child Division', distance: 'Varies', phone: '181', open: true, lat: null, lng: null },
    ]);
    setLoading(false);
  };

  const getDistance = (lat1, lng1, lat2, lng2) => {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
    const dist = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return `${dist.toFixed(1)} km`;
  };

  const openDirections = (station) => {
    if (station.lat && station.lng) {
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${station.lat},${station.lng}`, '_blank');
    } else if (location) {
      window.open(`https://www.google.com/maps/search/police+station/@${location.lat},${location.lng},14z`, '_blank');
    } else {
      window.open('https://www.google.com/maps/search/police+station+near+me', '_blank');
    }
  };

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto space-y-8 pb-16">

        {/* Header */}
        <div className="space-y-3">
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '42px', height: '42px', borderRadius: '12px',
              background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 20px rgba(212,175,55,0.35)',
              flexShrink: 0,
            }}>
              <MapPin size={20} color="#0B0B0B" />
            </div>
            <h1 style={{
              fontSize: '34px', fontWeight: '800',
              fontFamily: "'Georgia', 'Times New Roman', serif",
              background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.5px',
            }}>Nearby Police Stations</h1>
          </div>
          <p style={{ color: '#A1A1AA', fontFamily: 'system-ui, sans-serif', fontSize: '15px' }}>
            Find the nearest police station to file your FIR or report a crime.
          </p>
        </div>

        {/* Emergency Banner */}
        <div style={{
          background: 'rgba(239,68,68,0.08)',
          border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: '16px',
          padding: '18px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          backdropFilter: 'blur(12px)',
          boxShadow: '0 4px 20px rgba(239,68,68,0.1)',
        }}>
          <div style={{ fontSize: '28px' }}>🚨</div>
          <div style={{ flex: 1 }}>
            <p style={{ fontWeight: '700', color: '#FCA5A5', fontFamily: 'system-ui, sans-serif', marginBottom: '2px' }}>
              Emergency? Call immediately
            </p>
            <p style={{ fontSize: '13px', color: '#F87171', fontFamily: 'system-ui, sans-serif' }}>
              Police: 100 · Emergency: 112 · Women Helpline: 181
            </p>
          </div>
          <a
            href="tel:112"
            style={{
              background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: 'white',
              padding: '10px 20px',
              borderRadius: '10px',
              fontWeight: '600',
              fontSize: '13px',
              textDecoration: 'none',
              boxShadow: '0 4px 15px rgba(239,68,68,0.4)',
              transition: 'all 0.2s',
              fontFamily: 'system-ui, sans-serif',
              whiteSpace: 'nowrap',
            }}
          >
            Call 112
          </a>
        </div>

        {/* Location Button */}
        {!location && !loading && stations.length === 0 && (
          <div style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(212,175,55,0.2)',
            borderRadius: '20px',
            padding: '56px 40px',
            textAlign: 'center',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
          }}>
            <div style={{ fontSize: '52px', marginBottom: '16px' }}>📍</div>
            <h2 style={{
              fontSize: '20px', fontWeight: '700',
              fontFamily: "'Georgia', 'Times New Roman', serif",
              color: '#E5E5E5', marginBottom: '10px',
            }}>Find Stations Near You</h2>
            <p style={{ color: '#A1A1AA', fontSize: '14px', maxWidth: '380px', margin: '0 auto 28px', fontFamily: 'system-ui, sans-serif', lineHeight: '1.6' }}>
              Allow location access to find police stations within 5km of your current location.
            </p>
            <button
              onClick={getLocation}
              style={{
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                color: '#0B0B0B',
                padding: '13px 36px',
                borderRadius: '12px',
                fontWeight: '700',
                fontSize: '15px',
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 6px 24px rgba(212,175,55,0.45)',
                transition: 'all 0.2s ease',
                fontFamily: 'system-ui, sans-serif',
                display: 'block',
                margin: '0 auto 16px',
              }}
              onMouseEnter={e => { e.target.style.transform = 'translateY(-2px)'; e.target.style.boxShadow = '0 10px 32px rgba(212,175,55,0.6)'; }}
              onMouseLeave={e => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 6px 24px rgba(212,175,55,0.45)'; }}
            >
              📍 Use My Location
            </button>
            <button
              onClick={loadMockStations}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#A1A1AA',
                fontSize: '13px',
                cursor: 'pointer',
                fontFamily: 'system-ui, sans-serif',
                transition: 'color 0.2s',
                display: 'block',
                margin: '0 auto',
              }}
              onMouseEnter={e => e.target.style.color = '#D4AF37'}
              onMouseLeave={e => e.target.style.color = '#A1A1AA'}
            >
              Skip — show general information
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '56px 0' }}>
            <div style={{
              width: '48px', height: '48px',
              border: '3px solid rgba(212,175,55,0.2)',
              borderTop: '3px solid #D4AF37',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <p style={{ color: '#A1A1AA', fontFamily: 'system-ui, sans-serif' }}>Finding nearby police stations...</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.3)',
            borderRadius: '14px',
            padding: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}>
            <AlertCircle size={18} style={{ color: '#FCD34D', flexShrink: 0, marginTop: '2px' }} />
            <div>
              <p style={{ color: '#FDE68A', fontSize: '14px', fontWeight: '500', fontFamily: 'system-ui, sans-serif' }}>{error}</p>
              {permissionDenied && (
                <p style={{ color: '#D4AF37', fontSize: '12px', marginTop: '4px', fontFamily: 'system-ui, sans-serif' }}>
                  Showing general police contact information instead.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Stations List */}
        {stations.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{
                fontSize: '20px', fontWeight: '700',
                fontFamily: "'Georgia', 'Times New Roman', serif",
                color: '#E5E5E5',
              }}>
                {location ? 'Stations near you' : 'Police Contacts'}
              </h2>
              {location && (
                <button
                  onClick={getLocation}
                  style={{
                    background: 'transparent', border: 'none',
                    color: '#A1A1AA', fontSize: '13px', cursor: 'pointer',
                    fontFamily: 'system-ui, sans-serif', transition: 'color 0.2s',
                  }}
                  onMouseEnter={e => e.target.style.color = '#D4AF37'}
                  onMouseLeave={e => e.target.style.color = '#A1A1AA'}
                >
                  Refresh
                </button>
              )}
            </div>

            {stations.map((station, index) => (
              <motion.div
                key={station.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08 }}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(212,175,55,0.18)',
                  borderRadius: '14px',
                  padding: '20px',
                  backdropFilter: 'blur(12px)',
                  transition: 'all 0.25s ease',
                  cursor: 'default',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.border = '1px solid rgba(212,175,55,0.4)';
                  e.currentTarget.style.boxShadow = '0 8px 28px rgba(212,175,55,0.1)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.border = '1px solid rgba(212,175,55,0.18)';
                  e.currentTarget.style.boxShadow = 'none';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                      <h3 style={{ fontWeight: '700', color: '#E5E5E5', fontFamily: 'system-ui, sans-serif', fontSize: '15px' }}>
                        {station.name}
                      </h3>
                      {station.open && (
                        <span style={{
                          fontSize: '11px',
                          background: 'rgba(34,197,94,0.15)',
                          color: '#86EFAC',
                          padding: '2px 8px',
                          borderRadius: '20px',
                          border: '1px solid rgba(34,197,94,0.3)',
                          fontFamily: 'system-ui, sans-serif',
                        }}>Open</span>
                      )}
                    </div>
                    <p style={{ fontSize: '13px', color: '#A1A1AA', display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'system-ui, sans-serif' }}>
                      <MapPin size={12} style={{ color: '#D4AF37' }} /> {station.address}
                    </p>
                    {station.distance && (
                      <p style={{ fontSize: '12px', color: '#71717A', marginTop: '4px', fontFamily: 'system-ui, sans-serif' }}>
                        {station.distance} away
                      </p>
                    )}
                    {station.rating && (
                      <p style={{ fontSize: '12px', color: '#D4AF37', marginTop: '2px', fontFamily: 'system-ui, sans-serif' }}>
                        ⭐ {station.rating}
                      </p>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexShrink: 0, marginLeft: '16px' }}>
                    {station.phone && (
                      <a
                        href={`tel:${station.phone}`}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px',
                          background: 'rgba(34,197,94,0.1)',
                          color: '#86EFAC',
                          padding: '8px 14px',
                          borderRadius: '10px',
                          fontSize: '13px',
                          fontWeight: '600',
                          textDecoration: 'none',
                          border: '1px solid rgba(34,197,94,0.25)',
                          transition: 'all 0.2s',
                          fontFamily: 'system-ui, sans-serif',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(34,197,94,0.2)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(34,197,94,0.1)'; }}
                      >
                        <Phone size={14} /> {station.phone}
                      </a>
                    )}
                    <button
                      onClick={() => openDirections(station)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        background: 'rgba(212,175,55,0.1)',
                        color: '#D4AF37',
                        padding: '8px 14px',
                        borderRadius: '10px',
                        fontSize: '13px',
                        fontWeight: '600',
                        border: '1px solid rgba(212,175,55,0.25)',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        fontFamily: 'system-ui, sans-serif',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.2)'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.1)'; }}
                    >
                      <Navigation size={14} /> Directions
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Tips */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(212,175,55,0.08) 0%, rgba(197,164,109,0.05) 100%)',
          border: '1px solid rgba(212,175,55,0.2)',
          borderRadius: '20px',
          padding: '28px',
          backdropFilter: 'blur(12px)',
        }}>
          <h3 style={{
            fontWeight: '700', color: '#D4AF37', marginBottom: '16px',
            fontFamily: "'Georgia', 'Times New Roman', serif", fontSize: '17px',
            display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            💡 Before You Go
          </h3>
          <ul style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              'Carry a government-issued ID (Aadhar, PAN, Voter ID)',
              'Bring any evidence — photos, screenshots, documents',
              'Note down witness names and contact numbers',
              'You can file a Zero FIR at any station regardless of jurisdiction',
              'Request a free copy of your FIR after registration',
              'If refused, contact the SP/DCP of your district',
            ].map((tip, i) => (
              <li key={i} style={{
                fontSize: '14px', color: '#E5E5E5', fontFamily: 'system-ui, sans-serif',
                display: 'flex', alignItems: 'flex-start', gap: '10px', lineHeight: '1.5',
              }}>
                <span style={{ color: '#D4AF37', fontWeight: '700', flexShrink: 0 }}>›</span>
                {tip}
              </li>
            ))}
          </ul>
        </div>

      </div>
    </PageTransition>
  );
};

export default NearbyStationsPage;
