export const validateEmail = (email) => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
};

export const validatePhone = (phone) => {
  const regex = /^[6-9]\d{9}$/; // Indian 10-digit number
  return regex.test(phone);
};

export const validateRequiredFields = (data) => {
  for (let key in data) {
    if (!data[key]) {
      return false;
    }
  }
  return true;
};

export const validateFIRForm = (formData) => {
  if (!formData.fullName) return "Full Name is required";
  if (!validatePhone(formData.contact))
    return "Invalid phone number";
  if (!validateEmail(formData.email))
    return "Invalid email address";
  if (!formData.description)
    return "Incident description is required";

  return null; // No error
};
