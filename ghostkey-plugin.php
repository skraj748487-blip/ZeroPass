<?php
/**
 * Plugin Name: GhostKey Sovereign Biometric Login
 * Description: Zero-password, hardware-bound WebAuthn biometric login for WordPress.
 * Version: 1.0.0
 * Author: Sahil Ahmad
 */

if (!defined('ABSPATH')) exit;

add_action('login_enqueue_scripts', 'ghostkey_enqueue_scripts');
function ghostkey_enqueue_scripts() {
    wp_enqueue_script('ghostkey-sdk', 'https://zeropass1.onrender.com/airauth.js', array(), '1.0', true);
}

add_action('login_form', 'ghostkey_add_login_button');
function ghostkey_add_login_button() {
    echo '
    <div style="margin: 15px 0; text-align: center;">
        <button type="button" onclick="GhostKeyLoginTrigger()" style="width: 100%; padding: 12px; background: #0284c7; color: #fff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">
            ⚡ Sign In with GhostKey Fingerprint
        </button>
    </div>
    <script>
    function GhostKeyTrigger() {
        AirAuth.login(function(res) {
            if(res.success) {
                alert("Identity Authenticated: " + res.user);
            }
        });
    }
    </script>
    ';
}
