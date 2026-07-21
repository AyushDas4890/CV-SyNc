const axios = require("axios");
const crypto = require("crypto");
const config = require("../config/env");

const GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo";

function buildGoogleAuthorizeUrl(state) {
  const params = new URLSearchParams({
    client_id: config.google.clientId,
    redirect_uri: config.google.callbackUrl,
    response_type: "code",
    scope: "openid email profile",
    state,
    access_type: "offline",
    prompt: "select_account", // always show account picker
  });
  return `${GOOGLE_AUTHORIZE_URL}?${params.toString()}`;
}

function generateState() {
  return crypto.randomBytes(16).toString("hex");
}

async function exchangeCodeForToken(code) {
  const res = await axios.post(GOOGLE_TOKEN_URL, {
    client_id: config.google.clientId,
    client_secret: config.google.clientSecret,
    redirect_uri: config.google.callbackUrl,
    grant_type: "authorization_code",
    code,
  });
  return res.data; // { access_token, id_token, expires_in, ... }
}

async function fetchGoogleUser(accessToken) {
  const res = await axios.get(GOOGLE_USERINFO_URL, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  // { sub, email, name, picture, email_verified }
  return res.data;
}

module.exports = {
  buildGoogleAuthorizeUrl,
  generateState,
  exchangeCodeForToken,
  fetchGoogleUser,
};
