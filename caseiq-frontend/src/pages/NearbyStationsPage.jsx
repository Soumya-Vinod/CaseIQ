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
          distance: getDistance(
            lat, lng,
            place.geometry.location.lat,
            place.geometry.location.lng
          ),
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
      {
        id: 1,
        name: 'Local Police Station',
        address: 'Based on your area',
        distance: '< 2 km',
        phone: '100',
        open: true,
        lat: null,
        lng: null,
      },
      {
        id: 2,
        name: 'District Police Headquarters',
        address: 'District HQ',
        distance: '< 5 km',
        phone: '100',
        open: true,
        lat: null,
        lng: null,
      },
      {
        id: 3,
        name: 'Cyber Crime Cell',
        address: 'Cyber Police Station',
        distance: 'Varies',
        phone: '1930',
        open: true,
        lat: null,
        lng: null,
      },
      {
        id: 4,
        name: 'Women Police Station',
        address: 'Women & Child Division',
        distance: 'Varies',
        phone: '181',
        open: true,
        lat: null,
        lng: null,
      },
    ]);
    setLoading(false);
  };

  const getDistance = (lat1, lng1, lat2, lng2) => {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1 * Math.PI / 180) *
      Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) ** 2;
    const dist = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return `${dist.toFixed(1)} km`;
  };

  const openDirections = (station) => {
    if (station.lat && station.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${station.lat},${station.lng}`,
        '_blank'
      );
    } else if (location) {
      window.open(
        `https://www.google.com/maps/search/police+station/@${location.lat},${location.lng},14z`,
        '_blank'
      );
    } else {
      window.open(
        'https://www.google.com/maps/search/police+station+near+me',
        '_blank'
      );
    }
  };

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto space-y-8 pb-16">

        {/* Header */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <MapPin className="text-[#443627]" size={28} />
            <h1 className="text-4xl font-bold text-[#443627]">Nearby Police Stations</h1>
          </div>
          <p className="text-[#725E54]">
            Find the nearest police station to file your FIR or report a crime.
          </p>
        </div>

        {/* Emergency Banner */}
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-4">
          <div className="text-3xl">🚨</div>
          <div className="flex-1">
            <p className="font-semibold text-red-800">Emergency? Call immediately</p>
            <p className="text-sm text-red-600">
              Police: 100 · Emergency: 112 · Women Helpline: 181
            </p>
          </div>
          <a
            href="tel:112"
            className="bg-red-600 text-white px-4 py-2 rounded-xl font-medium hover:bg-red-700 transition text-sm"
          >
            Call 112
          </a>
        </div>

        {/* Location Button */}
        {!location && !loading && stations.length === 0 && (
          <div className="bg-white rounded-3xl p-10 text-center border border-[#D5DCF9] shadow space-y-5">
            <div className="text-5xl">📍</div>
            <h2 className="text-xl font-semibold text-[#443627]">Find Stations Near You</h2>
            <p className="text-[#725E54] text-sm max-w-md mx-auto">
              Allow location access to find police stations within 5km of your current location.
            </p>
            <button
              onClick={getLocation}
              className="bg-[#443627] text-white px-8 py-3 rounded-xl hover:bg-[#725E54] transition shadow-lg font-medium"
            >
              📍 Use My Location
            </button>
            <button
              onClick={loadMockStations}
              className="block w-full text-sm text-slate-400 hover:text-[#443627] transition mt-2"
            >
              Skip — show general information
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center gap-4 py-12">
            <div className="w-12 h-12 border-4 border-[#443627] border-t-transparent rounded-full animate-spin" />
            <p className="text-[#725E54]">Finding nearby police stations...</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start gap-3">
            <AlertCircle size={18} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-amber-800 text-sm font-medium">{error}</p>
              {permissionDenied && (
                <p className="text-amber-600 text-xs mt-1">
                  Showing general police contact information instead.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Stations List */}
        {stations.length > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold text-[#443627]">
                {location ? 'Stations near you' : 'Police Contacts'}
              </h2>
              {location && (
                <button
                  onClick={getLocation}
                  className="text-sm text-[#725E54] hover:text-[#443627] transition"
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
                className="bg-white rounded-2xl p-5 shadow border border-[#D5DCF9] hover:shadow-md transition"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-[#443627]">{station.name}</h3>
                      {station.open && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                          Open
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[#725E54] flex items-center gap-1">
                      <MapPin size={12} /> {station.address}
                    </p>
                    {station.distance && (
                      <p className="text-xs text-slate-400 mt-1">{station.distance} away</p>
                    )}
                    {station.rating && (
                      <p className="text-xs text-slate-400">⭐ {station.rating}</p>
                    )}
                  </div>

                  <div className="flex gap-2 shrink-0 ml-4">
                    {station.phone && (
                    <a
                        href={`tel:${station.phone}`}
                        className="flex items-center gap-1 bg-green-100 text-green-700 px-3 py-2 rounded-xl text-sm hover:bg-green-200 transition font-medium"
                    >
                        <Phone size={14} /> {station.phone}
                    </a>
                    )}
                    <button
                      onClick={() => openDirections(station)}
                      className="flex items-center gap-1 bg-[#D5DCF9] text-[#443627] px-3 py-2 rounded-xl text-sm hover:bg-[#A7B0CA] transition font-medium"
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
        <div className="bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6]/40 rounded-3xl p-6 space-y-3">
          <h3 className="font-semibold text-[#443627]">💡 Before You Go</h3>
          <ul className="space-y-2 text-sm text-[#443627]/80">
            <li>• Carry a government-issued ID (Aadhar, PAN, Voter ID)</li>
            <li>• Bring any evidence — photos, screenshots, documents</li>
            <li>• Note down witness names and contact numbers</li>
            <li>• You can file a Zero FIR at any station regardless of jurisdiction</li>
            <li>• Request a free copy of your FIR after registration</li>
            <li>• If refused, contact the SP/DCP of your district</li>
          </ul>
        </div>

      </div>
    </PageTransition>
  );
};

export default NearbyStationsPage;