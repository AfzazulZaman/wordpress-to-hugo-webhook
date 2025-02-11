<!-- function send_post_to_hugo($post_id) {
    $url = "http://localhost:8083/?api_key=cbcaafhwsllintiybhs9hmvz3slesmkalverqwrzlc460fyagtxw8lgttdypm6r8";
    
    $post = get_post($post_id);
    $data = [
        'id' => $post->ID,
        'title' => $post->post_title,
        'content' => $post->post_content,
        'status' => $post->post_status
    ];

    wp_remote_post($url, [
        'body' => json_encode($data),
        'headers' => [
            'Content-Type' => 'application/json'
        ]
    ]);
}

add_action('save_post', 'send_post_to_hugo');
add_action('delete_post', 'send_post_to_hugo'); -->
<?php
// Add this to your theme's functions.php

// Configuration
define('HUGO_WEBHOOK_URL', 'http://localhost:8083');
define('HUGO_API_KEY', 'cbcaafhwsllintiybhs9hmvz3slesmkalverqwrzlc460fyagtxw8lgttdypm6r8');

/**
 * Send post data to Hugo webhook
 */
function send_post_to_hugo($post_id) {
    // Don't process auto-saves or revisions
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) return;
    if (wp_is_post_revision($post_id)) return;
    if (wp_is_post_autosave($post_id)) return;

    // Get post data
    $post = get_post($post_id);
    
    // Only process posts and pages
    if (!in_array($post->post_type, array('post', 'page'))) return;

    // Get post meta and taxonomies
    $categories = wp_get_post_categories($post_id, array('fields' => 'names'));
    $tags = wp_get_post_tags($post_id, array('fields' => 'names'));
    
    // Get featured image if exists
    $featured_image_url = '';
    if (has_post_thumbnail($post_id)) {
        $featured_image_url = get_the_post_thumbnail_url($post_id, 'full');
    }

    // Get all images from post content
    $media_urls = array();
    if (preg_match_all('/<img[^>]+src=[\'"]([^\'"]+)[\'"][^>]*>/i', $post->post_content, $matches)) {
        $media_urls = $matches[1];
    }

    // Prepare post data
    $data = array(
        'id' => $post->ID,
        'title' => $post->post_title,
        'content' => $post->post_content,
        'excerpt' => $post->post_excerpt,
        'slug' => $post->post_name,
        'status' => $post->post_status,
        'date' => $post->post_date,
        'modified_date' => $post->post_modified,
        'categories' => $categories,
        'tags' => $tags,
        'featured_image' => $featured_image_url,
        'media_urls' => $media_urls,
        'post_type' => $post->post_type,
        'action' => current_action() // save_post or delete_post
    );

    // Send to Hugo webhook
    $response = wp_remote_post(HUGO_WEBHOOK_URL . '/?api_key=' . HUGO_API_KEY, array(
        'body' => json_encode($data),
        'headers' => array(
            'Content-Type' => 'application/json'
        ),
        'timeout' => 30
    ));

    // Log errors if any
    if (is_wp_error($response)) {
        error_log('Hugo Webhook Error: ' . $response->get_error_message());
    } else {
        $response_code = wp_remote_retrieve_response_code($response);
        if ($response_code !== 200) {
            error_log('Hugo Webhook Error: Received response code ' . $response_code);
        }
    }
}

/**
 * Handle media uploads
 */
function send_media_to_hugo($attachment_id) {
    $attachment = get_post($attachment_id);
    if ($attachment->post_type !== 'attachment') return;

    $file_url = wp_get_attachment_url($attachment_id);
    $file_meta = wp_get_attachment_metadata($attachment_id);

    $data = array(
        'id' => $attachment_id,
        'title' => $attachment->post_title,
        'url' => $file_url,
        'mime_type' => $attachment->post_mime_type,
        'alt_text' => get_post_meta($attachment_id, '_wp_attachment_image_alt', true),
        'metadata' => $file_meta,
        'action' => 'upload_media'
    );

    wp_remote_post(HUGO_WEBHOOK_URL . '/?api_key=' . HUGO_API_KEY, array(
        'body' => json_encode($data),
        'headers' => array(
            'Content-Type' => 'application/json'
        ),
        'timeout' => 30
    ));
}

/**
 * Handle media deletions
 */
function handle_media_deletion($attachment_id) {
    $data = array(
        'id' => $attachment_id,
        'action' => 'delete_media'
    );

    wp_remote_post(HUGO_WEBHOOK_URL . '/?api_key=' . HUGO_API_KEY, array(
        'body' => json_encode($data),
        'headers' => array(
            'Content-Type' => 'application/json'
        ),
        'timeout' => 30
    ));
}

// Hook into WordPress actions
add_action('save_post', 'send_post_to_hugo', 10, 1);
add_action('delete_post', 'send_post_to_hugo', 10, 1);
add_action('add_attachment', 'send_media_to_hugo', 10, 1);
add_action('edit_attachment', 'send_media_to_hugo', 10, 1);
add_action('delete_attachment', 'handle_media_deletion', 10, 1);

/**
 * Add webhook status check to admin footer
 */
function check_hugo_webhook_status() {
    if (is_admin()) {
        $response = wp_remote_get(HUGO_WEBHOOK_URL . '/?api_key=' . HUGO_API_KEY);
        $status = is_wp_error($response) ? 'offline' : 'online';
        echo '<div class="hugo-webhook-status">Hugo Webhook Status: ' . ucfirst($status) . '</div>';
    }
}
add_action('admin_footer', 'check_hugo_webhook_status');

// Optional: Add admin notice if webhook is offline
function hugo_webhook_admin_notice() {
    $response = wp_remote_get(HUGO_WEBHOOK_URL . '/?api_key=' . HUGO_API_KEY);
    if (is_wp_error($response)) {
        ?>
        <div class="notice notice-error">
            <p>Warning: Hugo webhook server is not responding. Your posts may not be syncing to Hugo.</p>
        </div>
        <?php
    }
}
add_action('admin_notices', 'hugo_webhook_admin_notice');