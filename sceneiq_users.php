<?php
    // sceneiq_users.php - Member Portal for SceneIQ
    session_name('SCENEIQ_MEMBER_SESSION');
    session_start();
    if (empty($_SESSION['password_csrf_token'])) {
        $_SESSION['password_csrf_token'] = bin2hex(random_bytes(32));
    }

    // Enable error reporting for debugging
    error_reporting(E_ALL);
    ini_set('display_errors', 1);

    // Database configuration
    $host = 'sql201.infinityfree.com';
    $dbname = 'if0_40367004_automation_tree';
    $username = 'if0_40367004';
    $password = 'NkwFAH15FRIlvCf';

    try {
        $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    } catch(PDOException $e) {
        die("Connection failed: " . $e->getMessage());
    }


    // ===== MEMBER LOGIN / LOGOUT GATE =====
    // This portal has its own session and cannot use the administrator's selected-account session.
    $memberId = (int)($_SESSION['member_user_id'] ?? 0);

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['member_logout'])) {
        $_SESSION = [];
        if (ini_get('session.use_cookies')) {
            $params = session_get_cookie_params();
            setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
        }
        session_destroy();
        header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
        exit;
    }

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['member_login'])) {
        $loginIdentity = trim((string)($_POST['login_identity'] ?? ''));
        $loginPassword = (string)($_POST['login_password'] ?? '');
        try {
            $loginStmt = $pdo->prepare('SELECT id, email, username, password FROM users WHERE email = :email OR username = :username LIMIT 1');
            $loginStmt->execute([':email' => $loginIdentity, ':username' => $loginIdentity]);
            $loginUser = $loginStmt->fetch(PDO::FETCH_ASSOC);
            if ($loginUser && password_verify($loginPassword, (string)$loginUser['password'])) {
                session_regenerate_id(true);
                $_SESSION['member_user_id'] = (int)$loginUser['id'];
                $_SESSION['selected_user_id'] = (int)$loginUser['id'];
                $_SESSION['password_csrf_token'] = bin2hex(random_bytes(32));
                unset($_SESSION['member_login_error'], $_SESSION['flash_error'], $_SESSION['flash_success']);
                header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
                exit;
            }
            $_SESSION['member_login_error'] = 'Unable to sign in with those credentials. Please verify your details or contact management for assistance.';
            header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
            exit;
        } catch (Throwable $e) {
            error_log('SceneIQ member login failed: ' . $e->getMessage());
            $_SESSION['member_login_error'] = 'We are unable to sign you in at this time. Please contact management for assistance.';
            header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
            exit;
        }
    }

    if ($memberId <= 0) {
        $loginError = (string)($_SESSION['member_login_error'] ?? '');
        unset($_SESSION['member_login_error']);
        ?>
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>SceneIQ Member - Sign In</title>
            <style>
                *{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#f8fafc;color:#0f172a}
                .login-shell{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:22px}
                .login-card{width:100%;max-width:430px;background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:30px;box-shadow:0 12px 36px rgba(15,23,42,.09)}
                .login-brand{background:linear-gradient(135deg,#00695c 0%,#00897b 50%,#26a69a 100%);color:#fff;margin:-30px -30px 25px;padding:25px 30px;border-radius:18px 18px 0 0}
                .login-brand h1{font-size:23px;margin:0 0 6px}.login-brand p{margin:0;font-size:13px;opacity:.9}
                .login-card h2{font-size:20px;margin:0 0 7px}.login-intro{font-size:13px;line-height:1.6;color:#64748b;margin:0 0 22px}
                .login-field{margin-bottom:16px}.login-field label{display:block;font-size:13px;font-weight:650;margin-bottom:7px;color:#334155}
                .login-field input{width:100%;padding:12px 13px;border:1px solid #cbd5e1;border-radius:9px;font-size:15px;outline:none}
                .login-field input:focus{border-color:#00897b;box-shadow:0 0 0 3px rgba(0,137,123,.12)}
                .login-submit{width:100%;border:0;border-radius:9px;padding:13px;background:#00796b;color:#fff;font-size:15px;font-weight:700;cursor:pointer}
                .login-submit:hover{background:#00695c}.login-error{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:9px;padding:12px;font-size:13px;line-height:1.5;margin-bottom:17px}
                .login-footer{text-align:center;color:#94a3b8;font-size:11px;margin-top:20px}
            </style>
        </head>
        <body><main class="login-shell"><section class="login-card">
            <div class="login-brand"><h1>SceneIQ <span style="font-weight:300;opacity:.8"></span></h1><p>Member access portal</p></div>
            <h2>Sign in to your account</h2><p class="login-intro">Enter the login details provided to you by management.</p>
            <?php if ($loginError !== ''): ?><div class="login-error"><?php echo htmlspecialchars($loginError, ENT_QUOTES, 'UTF-8'); ?></div><?php endif; ?>
            <form method="POST" autocomplete="on">
                <div class="login-field"><label for="login_identity">Email or username</label><input id="login_identity" name="login_identity" type="text" autocomplete="username" required autofocus></div>
                <div class="login-field"><label for="login_password">Password</label><input id="login_password" name="login_password" type="password" autocomplete="current-password" required></div>
                <button class="login-submit" type="submit" name="member_login" value="1">Sign In</button>
            </form>
            <div class="login-footer">Authorized  only · Contact management if you need assistance.</div>
        </section></main></body></html>
        <?php
        exit;
    }

    // Always scope the existing member-facing interface to the authenticated account.
    $_SESSION['selected_user_id'] = $memberId;

    // ===== FUNCTIONS =====

    function getAllUsers($pdo) {
        $stmt = $pdo->query("SELECT id, email, username, created_at FROM users ORDER BY username");
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }

    function getUserById($pdo, $userId) {
        $stmt = $pdo->prepare("SELECT id, email, username, created_at FROM users WHERE id = :id");
        $stmt->execute([':id' => $userId]);
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }

    function createUser($pdo, $email, $username, $password) {
        $hashedPassword = password_hash($password, PASSWORD_DEFAULT);
        $stmt = $pdo->prepare("INSERT INTO users (email, username, password) VALUES (:email, :username, :password)");
        return $stmt->execute([
            ':email' => $email,
            ':username' => $username,
            ':password' => $hashedPassword
        ]);
    }

    function deleteUser($pdo, $userId) {
        $stmt = $pdo->prepare("DELETE FROM users WHERE id = :id");
        return $stmt->execute([':id' => $userId]);
    }

    function getGlobalConfig($pdo) {
        $stmt = $pdo->prepare("SELECT id, settings, dynamic_fields FROM sceneiq_config WHERE user_id = 0 ORDER BY id DESC LIMIT 1");
        $stmt->execute();
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }

    function getUserConfig($pdo, $userId) {
        $stmt = $pdo->prepare("SELECT id, settings, dynamic_fields, dynamic_tabs FROM sceneiq_config WHERE user_id = :user_id ORDER BY id DESC LIMIT 1");
        $stmt->execute([':user_id' => $userId]);
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }

    function saveGlobalConfig($pdo, $settings, $dynamicFields) {
        $config = getGlobalConfig($pdo);
        
        if ($config) {
            $stmt = $pdo->prepare("UPDATE sceneiq_config SET settings = :settings, dynamic_fields = :dynamic_fields WHERE id = :id");
            return $stmt->execute([
                ':settings' => json_encode($settings),
                ':dynamic_fields' => json_encode($dynamicFields),
                ':id' => $config['id']
            ]);
        } else {
            $stmt = $pdo->prepare("INSERT INTO sceneiq_config (user_id, settings, dynamic_fields) VALUES (0, :settings, :dynamic_fields)");
            return $stmt->execute([
                ':settings' => json_encode($settings),
                ':dynamic_fields' => json_encode($dynamicFields)
            ]);
        }
    }

    function saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs = null) {
        $config = getUserConfig($pdo, $userId);
        
        if ($dynamicTabs === null) {
            $dynamicTabs = [];
        }
        
        // Ensure each tab has submit_tab property
        foreach ($dynamicTabs as &$tab) {
            if (!isset($tab['submit_tab'])) {
                $tab['submit_tab'] = true; // Default to true
            }
        }
        
        if ($config) {
            $stmt = $pdo->prepare("UPDATE sceneiq_config SET settings = :settings, dynamic_fields = :dynamic_fields, dynamic_tabs = :dynamic_tabs WHERE id = :id");
            return $stmt->execute([
                ':settings' => json_encode($settings),
                ':dynamic_fields' => json_encode($dynamicFields),
                ':dynamic_tabs' => json_encode($dynamicTabs),
                ':id' => $config['id']
            ]);
        } else {
            $stmt = $pdo->prepare("INSERT INTO sceneiq_config (user_id, settings, dynamic_fields, dynamic_tabs) VALUES (:user_id, :settings, :dynamic_fields, :dynamic_tabs)");
            return $stmt->execute([
                ':user_id' => $userId,
                ':settings' => json_encode($settings),
                ':dynamic_fields' => json_encode($dynamicFields),
                ':dynamic_tabs' => json_encode($dynamicTabs)
            ]);
        }
    }

    function repairSettings($settings) {
        if (!is_array($settings)) return [];
        if (isset($settings[0]) && is_array($settings[0])) {
            return array_values(array_filter($settings, function($item) {
                return is_array($item);
            }));
        }
        if (isset($settings['status']) || isset($settings['dynamic_values'])) {
            return [$settings];
        }
        $result = [];
        foreach ($settings as $key => $value) {
            if (is_array($value) && (isset($value['status']) || isset($value['dynamic_values']))) {
                $result[] = $value;
            }
        }
        return empty($result) ? $settings : $result;
    }


    //  can manage their projects and their own password, but cannot edit portal structure.
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $adminOnlyActions = [
            'create_user', 'delete_user', 'select_user', 'clear_user', 'set_dashboard_view',
            'save_global_dynamic_fields', 'update_global_field', 'save_global_single_field',
            'delete_global_dynamic_field', 'save_dynamic_tabs', 'save_submit_tabs',
            'delete_dynamic_tab'
        ];
        foreach ($adminOnlyActions as $adminAction) {
            if (isset($_POST[$adminAction])) {
                http_response_code(403);
                exit('This action is available to management only.');
            }
        }
    }

    // ===== HANDLE POST REQUESTS WITH PRG PATTERN =====
    $redirect = false;
    $debugMessages = [];

    // Create User
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['create_user'])) {
        $email = trim($_POST['email'] ?? '');
        $username = trim($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';
        
        if (!$email || !$username || !$password) {
            $_SESSION['flash_error'] = 'All fields are required.';
        } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $_SESSION['flash_error'] = 'Invalid email address.';
        } elseif (strlen($password) < 6) {
            $_SESSION['flash_error'] = 'Password must be at least 6 characters.';
        } else {
            try {
                if (createUser($pdo, $email, $username, $password)) {
                    $_SESSION['flash_success'] = 'User created successfully!';
                } else {
                    $_SESSION['flash_error'] = 'Failed to create user. Email or username may already exist.';
                }
            } catch (PDOException $e) {
                $_SESSION['flash_error'] = 'Error: ' . $e->getMessage();
            }
        }
        $redirect = true;
    }

    // Delete User
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_user'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        if ($userId > 0) {
            if (deleteUser($pdo, $userId)) {
                $_SESSION['flash_success'] = 'User deleted successfully!';
                if (isset($_SESSION['selected_user_id']) && $_SESSION['selected_user_id'] == $userId) {
                    unset($_SESSION['selected_user_id']);
                }
            } else {
                $_SESSION['flash_error'] = 'Failed to delete user.';
            }
        }
        $redirect = true;
    }

    // Select User (set session)
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['select_user'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        if ($userId > 0) {
            $_SESSION['selected_user_id'] = $userId;
            unset($_SESSION['dashboard_view']);
        }
        $redirect = true;
    }

    // Clear selected user (go to dashboard)
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['clear_user'])) {
        unset($_SESSION['selected_user_id']);
        $_SESSION['dashboard_view'] = 'initialize';
        $redirect = true;
    }

    // Set dashboard view
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['set_dashboard_view'])) {
        $_SESSION['dashboard_view'] = in_array(($_POST['view'] ?? 'initialize'), ['initialize', 'accounts', 'all_config'], true) ? $_POST['view'] : 'initialize';
        $redirect = true;
    }

    // Save Settings for selected user
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['save_settings'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        $settings = isset($_POST['settings']) ? json_decode($_POST['settings'], true) : [];
        
        if ($userId > 0 && is_array($settings)) {
            $settings = repairSettings($settings);
            $config = getUserConfig($pdo, $userId);
            $dynamicFields = $config ? json_decode($config['dynamic_fields'], true) : [];
            if (!is_array($dynamicFields)) $dynamicFields = [];
            $dynamicTabs = $config ? json_decode($config['dynamic_tabs'], true) : [];
            if (!is_array($dynamicTabs)) $dynamicTabs = [];
            
            if (saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs)) {
                $_SESSION['flash_success'] = 'Settings saved successfully!';
            } else {
                $_SESSION['flash_error'] = 'Failed to save settings.';
            }
        }
        $redirect = true;
    }

    // Handle Delete Entry for a user
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_entry'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        $index = intval($_POST['index'] ?? -1);
        
        if ($userId > 0 && $index >= 0) {
            $config = getUserConfig($pdo, $userId);
            if ($config) {
                $settings = json_decode($config['settings'], true) ?: [];
                if (!is_array($settings)) $settings = [];
                $settings = repairSettings($settings);
                
                if ($index < count($settings)) {
                    array_splice($settings, $index, 1);
                    $dynamicFields = json_decode($config['dynamic_fields'], true) ?: [];
                    $dynamicTabs = json_decode($config['dynamic_tabs'], true) ?: [];
                    $result = saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs);
                    
                    if ($result) {
                        $_SESSION['flash_success'] = 'Entry deleted successfully!';
                    } else {
                        $_SESSION['flash_error'] = 'Failed to delete entry.';
                    }
                } else {
                    $_SESSION['flash_error'] = 'Entry not found.';
                }
            } else {
                $_SESSION['flash_error'] = 'User config not found.';
            }
        }
        $redirect = true;
    }

    // Handle New Project for a user - UPDATED for submit tabs filtering
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['add_entry'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        $entryData = isset($_POST['entry_data']) ? json_decode($_POST['entry_data'], true) : [];
        
        if ($userId > 0 && is_array($entryData) && !empty($entryData)) {
            $config = getUserConfig($pdo, $userId);
            $globalDynamicFields = $config ? (json_decode($config['dynamic_fields'], true) ?: []) : [];
            
            // Member portal: submit the account's configured dynamic content directly.
            // Management controls field/tab definitions in sceneiq_server.php.
            $dynamicTabs = $config ? json_decode($config['dynamic_tabs'], true) : [];
            if (!is_array($dynamicTabs)) $dynamicTabs = [];
            $submittedFieldKeys = array_keys($globalDynamicFields);            
            $flatEntry = [];
            foreach ($entryData as $key => $value) {
                if (is_array($value) && isset($value['_object'])) {
                    if (in_array($key, $submittedFieldKeys)) {
                        $objectData = [];
                        $subFieldDefinitions = $globalDynamicFields[$key]['fieldkeyvalue'] ?? [];
                        foreach ($value as $subKey => $subValue) {
                            if ($subKey === '_object') {
                                continue;
                            }
                            $objectData[$subKey] = $subValue;
                        }
                        $flatEntry[$key] = $objectData;
                    }
                } else {
                    if (in_array($key, $submittedFieldKeys)) {
                        $flatEntry[$key] = $value;
                    }
                }
            }
            
            if ($config) {
                $settings = json_decode($config['settings'], true) ?: [];
                if (!is_array($settings)) $settings = [];
                $settings = repairSettings($settings);
                
                $newEntry = $flatEntry;
                $newEntry['status'] = 'pending';
                $newEntry['operation_status'] = 'entry_created: New Project added by admin';
                $settings[] = $newEntry;
                
                $dynamicFields = json_decode($config['dynamic_fields'], true) ?: [];
                saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs);
                $_SESSION['flash_success'] = 'Entry added successfully!';
            } else {
                $settings = [];
                $newEntry = $flatEntry;
                $newEntry['status'] = 'pending';
                $newEntry['operation_status'] = 'entry_created: New Project added by admin';
                $settings[] = $newEntry;
                saveUserConfig($pdo, $userId, $settings, [], $dynamicTabs);
                $_SESSION['flash_success'] = 'Entry added successfully!';
            }
        } else {
            $_SESSION['flash_error'] = 'No entry data provided.';
        }
        $redirect = true;
    }

    // Update entry status
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_entry_status'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        $index = intval($_POST['index'] ?? -1);
        $newStatus = $_POST['new_status'] ?? '';
        
        if ($userId > 0 && $index >= 0 && in_array($newStatus, ['pending', 'completed', 'aborted'])) {
            $config = getUserConfig($pdo, $userId);
            if ($config) {
                $settings = json_decode($config['settings'], true) ?: [];
                if (!is_array($settings)) $settings = [];
                $settings = repairSettings($settings);
                
                if ($index < count($settings)) {
                    $settings[$index]['status'] = $newStatus;
                    $dynamicFields = json_decode($config['dynamic_fields'], true) ?: [];
                    $dynamicTabs = json_decode($config['dynamic_tabs'], true) ?: [];
                    saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs);
                    $_SESSION['flash_success'] = 'Status updated successfully!';
                }
            }
        }
        $redirect = true;
    }

    // Update entry field data
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_entry_field'])) {
        $userId = (int)($_SESSION['member_user_id'] ?? 0);
        $index = intval($_POST['index'] ?? -1);
        $fieldKey = $_POST['field_key'] ?? '';
        $fieldValue = $_POST['field_value'] ?? '';
        
        if ($userId > 0 && $index >= 0 && $fieldKey) {
            $config = getUserConfig($pdo, $userId);
            if ($config) {
                $settings = json_decode($config['settings'], true) ?: [];
                if (!is_array($settings)) $settings = [];
                $settings = repairSettings($settings);
                
                if ($index < count($settings)) {
                    $dynamicFields = json_decode($config['dynamic_fields'], true) ?: [];
                    $settings[$index][$fieldKey] = $fieldValue;
                    $dynamicTabs = json_decode($config['dynamic_tabs'], true) ?: [];
                    saveUserConfig($pdo, $userId, $settings, $dynamicFields, $dynamicTabs);
                    $_SESSION['flash_success'] = 'Field updated successfully!';
                }
            }
        }
        $redirect = true;
    }

    // Show debug modal
    if (isset($_GET['show_debug'])) {
        $debugMessages = isset($_SESSION['debug_messages']) ? $_SESSION['debug_messages'] : ['No debug messages available'];
        echo '<!DOCTYPE html><html><head><title>Debug Info</title>';
        echo '<style>body{font-family:monospace;padding:20px;background:#1a1a2e;color:#fff;}';
        echo '.debug-box{background:#2d2d44;padding:20px;border-radius:10px;margin:10px 0;overflow:auto;max-height:80vh;}';
        echo '.debug-line{padding:4px 0;border-bottom:1px solid #3d3d5a;}';
        echo '.error{color:#ff6b6b;}';
        echo '.success{color:#51cf66;}';
        echo '.warning{color:#ffd93d;}';
        echo 'pre{background:#1a1a2e;padding:10px;border-radius:5px;overflow:auto;}';
        echo '
        /* ===== CLEAN, CONSISTENT DYNAMIC TABS EDITOR ===== */
        #dynamicTabsEditor { width: 100%; min-width: 0; }
        .dynamic-tabs-editor-header {
            display: flex; align-items: center; justify-content: space-between;
            gap: 16px; flex-wrap: wrap; margin-bottom: 18px;
            padding: 18px; background: #f8fafc; border: 1px solid #e2e8f0;
            border-radius: 14px;
        }
        .dynamic-tabs-editor-header h3 { color: #0f172a; font-size: 20px; margin: 0 0 5px; }
        .dynamic-tabs-editor-header p { color: #64748b; font-size: 13px; line-height: 1.5; margin: 0; max-width: 720px; }
        .dynamic-tabs-editor-list { display: flex; flex-direction: column; gap: 14px; }
        .tab-editor-item {
            width: 100%; min-width: 0; background: #fff; border: 1px solid #dbe3ea;
            border-radius: 13px; padding: 16px; margin: 0; box-shadow: 0 2px 7px rgba(15,23,42,.04);
        }
        .root-tab-editor-item { border-left: 4px solid #0f766e; }
        .sub-tab-editor-item { border-left: 3px solid #94a3b8; background: #fff; }
        .tab-editor-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
        .tab-editor-heading-copy { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
        .tab-editor-kind { font-size: 10px; letter-spacing: .09em; font-weight: 800; color: #0f766e; }
        .sub-tab-editor-item .tab-editor-kind { color: #64748b; }
        .tab-editor-title { color: #0f172a; font-size: 15px; overflow-wrap: anywhere; }
        .tab-editor-actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .nested-tab-editor-body { margin-top: 16px; display: block; }
        .tab-editor-item .form-group { margin-bottom: 14px; }
        .tab-editor-item .form-group label { font-size: 13px; font-weight: 650; color: #334155; }
        .tab-editor-item .form-group input[type="text"],
        .tab-editor-item .form-group select,
        .tab-editor-item .form-group textarea {
            width: 100%; max-width: 100%; min-width: 0; padding: 10px 12px;
            border: 1px solid #cbd5e1; border-radius: 8px; background: #fff;
            color: #0f172a; box-shadow: none; font-size: 14px !important;
        }
        .tab-editor-item .form-group input:focus,
        .tab-editor-item .form-group select:focus,
        .tab-editor-item .form-group textarea:focus {
            outline: none; border-color: #0f766e; box-shadow: 0 0 0 3px rgba(15,118,110,.12);
        }
        .tab-fields-toggle-list {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
            gap: 6px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 9px; background: #f8fafc;
        }
        .tab-field-option {
            display: flex; align-items: center; justify-content: space-between; gap: 12px;
            min-width: 0; padding: 9px 10px; border: 1px solid #e2e8f0;
            border-radius: 8px; background: #fff; cursor: pointer;
        }
        .tab-field-option input { flex: 0 0 auto; width: 16px; height: 16px; accent-color: #0f766e; }
        .tab-field-label { min-width: 0; overflow-wrap: anywhere; color: #334155; font-size: 12px; }
        .tab-field-label small { color: #64748b; }
        .tab-editor-empty-fields { color: #64748b; font-size: 12px; padding: 8px; margin: 0; }
        .tab-feature-options { display: flex; align-items: center; gap: 8px 18px; flex-wrap: wrap; padding: 12px; border: 1px solid #e2e8f0; border-radius: 9px; background: #f8fafc; }
        .tab-feature-options label { display: inline-flex; align-items: center; gap: 7px; color: #475569; font-size: 12px; cursor: pointer; }
        .tab-feature-options input { accent-color: #0f766e; }
        .tab-editor-help { margin-top: 6px; font-size: 12px; line-height: 1.5; color: #64748b; }
        .nested-sub-tabs-container { margin-top: 16px; padding: 14px; border: 1px solid #99f6e4; background: #f0fdfa; border-radius: 12px; }
        .nested-sub-tabs-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
        .nested-sub-tabs-heading strong { display: block; color: #115e59; font-size: 14px; }
        .nested-sub-tabs-heading p { margin: 4px 0 0; color: #64748b; font-size: 12px; }
        .nested-sub-tabs-list { display: flex; flex-direction: column; gap: 10px; }
        .nested-sub-tabs-list:empty { display: none; }
        .nested-sub-tabs-empty { padding: 12px; margin: 0; border: 1px dashed #99f6e4; border-radius: 8px; color: #64748b; font-size: 12px; text-align: center; }
        .dynamic-tabs-save-bar { display: flex; justify-content: flex-end; margin-top: 18px; padding: 14px 0 2px; }
        .tab-editor-empty-state { display: flex; flex-direction: column; gap: 5px; align-items: center; padding: 28px 16px; border: 1px dashed #cbd5e1; border-radius: 12px; color: #64748b; text-align: center; margin-bottom: 14px; }
        .tab-editor-empty-state strong { color: #334155; font-size: 14px; }
        #newProjectSubTabs { gap: 8px; padding: 4px 2px 10px; border-bottom: 1px solid #e2e8f0; }
        #newProjectSubTabs .dynamic-sub-tab-btn,
        .nested-project-tabs .nested-child-btn {
            border: 1px solid #e2e8f0; border-radius: 9px; padding: 9px 14px;
            background: #f8fafc; color: #475569; margin: 0; min-height: 38px;
            transition: background .15s ease, border-color .15s ease, color .15s ease;
        }
        #newProjectSubTabs .dynamic-sub-tab-btn.active,
        .nested-project-tabs .nested-child-btn.active {
            background: #e6fffb; border-color: #0f766e; color: #115e59; font-weight: 700;
        }
        .nested-project-tabs { padding: 14px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
        .nested-project-tabs .dynamic-sub-tabs { gap: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }
        .nested-child-content { min-width: 0; padding-top: 8px; }
        @media (max-width: 640px) {
            .dynamic-tabs-editor-header { padding: 14px; align-items: stretch; }
            .dynamic-tabs-editor-header > .btn { width: 100%; }
            .tab-editor-item { padding: 12px; }
            .nested-sub-tabs-container { padding: 10px; }
            .tab-editor-actions { width: 100%; }
            .tab-editor-actions .btn { flex: 1 1 auto; }
            .tab-fields-toggle-list { grid-template-columns: minmax(0, 1fr); }
            .dynamic-tabs-save-bar .btn { width: 100%; }
        }

    
/* ===== Dynamic tab editor interaction updates ===== */
#dynamicTabsEditor .tab-editor-heading {
    cursor: pointer;
}
#dynamicTabsEditor .tab-editor-heading:focus-visible {
    outline: 2px solid #087f75;
    outline-offset: -2px;
}
#dynamicTabsEditor .tab-editor-item:not(.is-expanded) .tab-delete-button {
    display: none !important;
}
#dynamicTabsEditor .tab-editor-item.is-expanded .tab-delete-button {
    display: inline-flex !important;
}
#dynamicTabsEditor .display-tab-setting select.display-tab-input {
    width: 100%;
    max-width: 220px;
    min-height: 40px;
    padding: 9px 12px;
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background: #fff;
    color: #172033;
    cursor: pointer;
}
#dynamicTabsEditor .tab-editor-heading .tab-editor-actions {
    cursor: default;
}
</style></head><body>';
        echo '<h1> Debug Information</h1>';
        echo '<div class="debug-box">';
        foreach ($debugMessages as $msg) {
            $class = '';
            if (strpos($msg, 'ERROR') !== false) $class = 'error';
            else if (strpos($msg, 'SUCCESS') !== false) $class = 'success';
            else if (strpos($msg, 'WARNING') !== false) $class = 'warning';
            echo '<div class="debug-line ' . $class . '">' . htmlspecialchars($msg) . '</div>';
        }
        echo '</div>';
        echo '<button onclick="window.close()" style="padding:10px 20px;margin-top:20px;cursor:pointer;">Close</button>';
        echo '<button onclick="location.href=\'sceneiq_server.php\'" style="padding:10px 20px;margin-top:20px;margin-left:10px;cursor:pointer;">Back to Admin</button>';
        echo '</body></html>';
        exit;
    }


    // Change password for the currently selected account.
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['change_account_password'])) {
        $userId = intval($_POST['password_user_id'] ?? 0);
        $newPassword = (string)($_POST['new_password'] ?? '');
        $confirmPassword = (string)($_POST['confirm_password'] ?? '');
        $postedToken = (string)($_POST['password_csrf_token'] ?? '');

        if (empty($_SESSION['password_csrf_token']) ||
            !hash_equals($_SESSION['password_csrf_token'], $postedToken)) {
            $_SESSION['flash_error'] = 'Security check failed. Please try again.';
        } elseif ($userId <= 0 || $userId !== intval($_SESSION['selected_user_id'] ?? 0)) {
            $_SESSION['flash_error'] = 'Please select the account whose password you want to change.';
        } elseif (strlen($newPassword) < 8) {
            $_SESSION['flash_error'] = 'Password must be at least 8 characters long.';
        } elseif ($newPassword !== $confirmPassword) {
            $_SESSION['flash_error'] = 'The new password and confirmation do not match.';
        } else {
            try {
                $hashedPassword = password_hash($newPassword, PASSWORD_DEFAULT);
                $stmt = $pdo->prepare('UPDATE users SET password = :password WHERE id = :id');
                $stmt->execute([':password' => $hashedPassword, ':id' => $userId]);
                if ($stmt->rowCount() > 0) {
                    $_SESSION['flash_success'] = 'Password changed successfully.';
                } else {
                    // rowCount can be zero when the value is unchanged; verify account exists.
                    $check = $pdo->prepare('SELECT id FROM users WHERE id = :id');
                    $check->execute([':id' => $userId]);
                    $exists = (bool)$check->fetchColumn();
                    $_SESSION[$exists ? 'flash_success' : 'flash_error'] =
                        $exists ? 'Password changed successfully.' : 'Account not found.';
                }
                $_SESSION['password_csrf_token'] = bin2hex(random_bytes(32));
            } catch (Throwable $e) {
                error_log('Password update failed: ' . $e->getMessage());
                $_SESSION['flash_error'] = 'Unable to change the password. Please try again.';
            }
        }
        $redirect = true;
    }

    // If any POST request that should redirect, do it here
    if ($redirect) {
        header('Location: ' . $_SERVER['PHP_SELF']);
        exit;
    }

    // ===== GET FLASH MESSAGES =====
    $flashSuccess = isset($_SESSION['flash_success']) ? $_SESSION['flash_success'] : null;
    $flashError = isset($_SESSION['flash_error']) ? $_SESSION['flash_error'] : null;
    $debugMessages = isset($_SESSION['debug_messages']) ? $_SESSION['debug_messages'] : [];
    unset($_SESSION['flash_success'], $_SESSION['flash_error'], $_SESSION['debug_messages']);

    // ===== GET DATA =====
    $users = getAllUsers($pdo);
    $selectedUserId = isset($_SESSION['selected_user_id']) ? intval($_SESSION['selected_user_id']) : 0;
    $dashboardView = isset($_SESSION['dashboard_view']) ? $_SESSION['dashboard_view'] : 'initialize';
    if (!in_array($dashboardView, ['initialize', 'accounts', 'all_config'], true)) { $dashboardView = 'initialize'; }

    $selectedUser = null;
    $userConfig = null;
    $userSettings = [];
    $userDynamicFields = [];
    $userDynamicTabs = [];
    // Dynamic fields are account-scoped; there is no shared/global field definition.
    $globalDynamicFields = [];

    $groupedEntries = ['pending' => [], 'completed' => [], 'aborted' => []];
    $statusLabels = ['pending' => 'Pending', 'completed' => 'Completed', 'aborted' => 'Aborted'];
    $statusColors = ['pending' => '#f59e0b', 'completed' => '#10b981', 'aborted' => '#ef4444'];
    $statusIcons = ['pending' => '', 'completed' => '', 'aborted' => ''];

    // For All Account Config - get all entries across all users
    $allUsersEntries = ['pending' => [], 'completed' => [], 'aborted' => []];
    foreach ($users as $user) {
        $userConf = getUserConfig($pdo, $user['id']);
        if ($userConf) {
            $settings = json_decode($userConf['settings'], true) ?: [];
            if (!is_array($settings)) $settings = [];
            $settings = repairSettings($settings);
            foreach ($settings as $index => $entry) {
                $status = isset($entry['status']) ? strtolower($entry['status']) : 'pending';
                $entry['_user'] = $user['username'];
                $entry['_user_id'] = $user['id'];
                $entry['_index'] = $index;
                $allUsersEntries[$status][] = $entry;
            }
        }
    }

    if ($selectedUserId > 0) {
        $selectedUser = getUserById($pdo, $selectedUserId);
        if ($selectedUser) {
            $userConfig = getUserConfig($pdo, $selectedUserId);
            if ($userConfig) {
                $userSettings = json_decode($userConfig['settings'], true) ?: [];
                if (!is_array($userSettings)) $userSettings = [];
                $userSettings = repairSettings($userSettings);
                
                $userDynamicFields = json_decode($userConfig['dynamic_fields'], true) ?: [];
                if (!is_array($userDynamicFields)) $userDynamicFields = [];
                
                $userDynamicTabs = json_decode($userConfig['dynamic_tabs'], true) ?: [];
                if (!is_array($userDynamicTabs)) $userDynamicTabs = [];
                
                foreach ($userSettings as $index => $entry) {
                    $status = isset($entry['status']) ? strtolower($entry['status']) : 'pending';
                    if (!isset($groupedEntries[$status])) {
                        $groupedEntries[$status] = [];
                    }
                    $entry['_index'] = $index;
                    $groupedEntries[$status][] = $entry;
                }
            } else {
                saveUserConfig($pdo, $selectedUserId, [], [], []);
                $userDynamicFields = [];
                $userDynamicTabs = [];
            }
        }
    }
    // Existing JavaScript uses this variable name; its data is now strictly per selected account.
    $globalDynamicFields = $userDynamicFields;
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SceneIQ </title>
<style>
        /* Member portal: retain the shared SceneIQ template while hiding management-only navigation. */
        .dashboard-layout { grid-template-columns: minmax(0, 1fr) !important; }
        .dashboard-layout > .sidebar, .dashboard-tabs, #dash_tab_initialize, #dash_tab_accounts, #dash_tab_all_config,
        .create-user-form, .accounts-list, #user_tab_dynamic_tabs, #user_tab_submit_tabs,
        #user_tab_dynamic_fields, .account-dynamic-fields-add-bar { display:none !important; }
        .user-config-tabs .user-config-tab-btn { display:inline-flex; }
        .copy-button-copied { background:#dcfce7 !important; border-color:#16a34a !important; color:#166534 !important; }

        /* ===== RESET & BODY ===== */
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        html, body { 
            height: 100%; 
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #ffffff;
        }
        
        input, select, textarea {
            font-size: 16px !important;
        }
        
        .custom-body {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            width: 100%;
            max-width: 100%;
        }
        
        /* ===== HEADER ===== */
        .main-header {
            flex-shrink: 0;
            z-index: 1000;
            background: linear-gradient(135deg, #00695c 0%, #00897b 50%, #26a69a 100%);
            color: white;
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,105,92,0.3);
            min-height: 60px;
            width: 100%;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .main-header h1 { 
            font-size: 18px; 
            font-weight: 600;
            white-space: nowrap;
        }
        .main-header h1 span { opacity: 0.6; font-weight: 300; }
        
        .debug-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            font-size: 14px;
            white-space: nowrap;
        }
        
        .debug-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        /* ===== SCROLLABLE BODY ===== */
        .scroll-body {
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
            padding: 0 15px 30px;
            padding-top: 0 !important;
            padding-bottom: 30px;
            background: #ffffff;
            width: 100%;
            max-width: 100%;
        }
        
        .scroll-body::-webkit-scrollbar {
            width: 6px;
        }
        
        .scroll-body::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.02);
            border-radius: 10px;
        }
        
        .scroll-body::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #00695c, #26a69a);
            border-radius: 10px;
        }
        
        .scroll-body::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #004d40, #00897b);
        }
        
        .server-container {
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            padding: 0 5px;
        }
        
        .two-col {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 20px;
            margin-top: 15px;
            width: 100%;
        }
        
        .sidebar {
            background: #ffffff;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.05);
            height: fit-content;
            width: 100%;
            min-width: 0;
            overflow: hidden;
        }
        
        .sidebar h2 {
            font-size: 16px;
            color: #1a1a2e;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .search-users-btn {
            width: 100%;
            padding: 10px 14px;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            color: #6b7280;
            transition: all 0.3s;
            margin-bottom: 12px;
            text-align: center;
        }
        
        .search-users-btn:hover {
            background: #e5e7eb;
            border-color: #00695c;
            color: #00695c;
        }
        
        .content-area {
            background: #ffffff;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.05);
            min-height: 400px;
            width: 100%;
            min-width: 0;
            overflow: hidden;
        }
        
        /* ===== DASHBOARD TABS - HORIZONTAL SCROLL ===== */
        .dashboard-tabs {
            display: flex;
            gap: 0;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            overflow-x: auto;
            overflow-y: hidden;
            width: 100%;
            white-space: nowrap;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch;
            align-items: stretch;
            min-height: 48px;
            flex-wrap: nowrap;
        }
        
        .dashboard-tabs::-webkit-scrollbar {
            height: 3px;
        }
        
        .dashboard-tabs::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .dashboard-tabs::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 10px;
        }
        
        .dashboard-tabs::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        .dashboard-tab-btn {
            padding: 10px 16px;
            background: none;
            border: none;
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            white-space: nowrap;
            flex-shrink: 0;
            min-height: 46px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .dashboard-tab-btn:hover {
            color: #1a1a2e;
        }
        
        .dashboard-tab-btn.active {
            color: #00695c;
            border-bottom-color: #00695c;
        }
        
        .dashboard-content {
            display: none;
            padding-top: 10px;
            width: 100%;
        }
        
        .dashboard-content.active {
            display: block;
        }
        
        /* ===== USER CONFIG TABS - HORIZONTAL SCROLL ===== */
        .user-config-tabs {
            display: flex;
            gap: 0;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            overflow-x: auto;
            overflow-y: hidden;
            width: 100%;
            white-space: nowrap;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch;
            align-items: stretch;
            min-height: 48px;
            flex-wrap: nowrap;
        }
        
        .user-config-tabs::-webkit-scrollbar {
            height: 3px;
        }
        
        .user-config-tabs::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .user-config-tabs::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 10px;
        }
        
        .user-config-tabs::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        .user-config-tab-btn {
            padding: 10px 16px;
            background: none;
            border: none;
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            white-space: nowrap;
            flex-shrink: 0;
            min-height: 46px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .user-config-tab-btn:hover {
            color: #1a1a2e;
        }
        
        .user-config-tab-btn.active {
            color: #00695c;
            border-bottom-color: #00695c;
        }
        
        .user-config-content {
            display: none;
            padding-top: 10px;
            width: 100%;
        }
        
        .user-config-content.active {
            display: block;
        }
        
        /* ===== DYNAMIC SUB TABS ===== */
        .dynamic-sub-tabs {
            display: flex;
            gap: 0;
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
            overflow-x: auto;
            overflow-y: hidden;
            width: 100%;
            white-space: nowrap;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch;
            align-items: stretch;
            min-height: 40px;
            flex-wrap: nowrap;
        }
        
        .dynamic-sub-tabs::-webkit-scrollbar {
            height: 3px;
        }
        
        .dynamic-sub-tabs::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .dynamic-sub-tabs::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 10px;
        }
        
        .dynamic-sub-tabs::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        .dynamic-sub-tab-btn {
            padding: 8px 14px;
            background: none;
            border: none;
            font-size: 13px;
            font-weight: 500;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            white-space: nowrap;
            flex-shrink: 0;
            min-height: 38px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .dynamic-sub-tab-btn:hover {
            color: #1a1a2e;
        }
        
        .dynamic-sub-tab-btn.active {
            color: #00695c;
            border-bottom-color: #00695c;
        }
        
        .dynamic-sub-tab-content {
            display: none;
            padding-top: 10px;
            width: 100%;
        }
        
        .dynamic-sub-tab-content.active {
            display: block;
        }
        
        .create-user-form {
            max-width: 500px;
            width: 100%;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        }
        
        .create-user-form h3 {
            font-size: 18px;
            color: #1a1a2e;
            margin-bottom: 15px;
            text-align: center;
        }
        
        .create-user-form .form-row {
            display: grid;
            gap: 10px;
            width: 100%;
        }
        
        .create-user-form input {
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
            background: white;
            width: 100%;
            box-sizing: border-box;
        }
        
        .create-user-form input:focus {
            border-color: #00695c;
            outline: none;
            box-shadow: 0 0 0 4px rgba(0,105,92,0.1);
        }
        
        .create-user-form .btn-create {
            padding: 12px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
            width: 100%;
        }
        
        .create-user-form .btn-create:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(16,185,129,0.3);
        }
        
        .form-group {
            margin-bottom: 18px;
            width: 100%;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #1a1a2e;
            font-size: 14px;
        }
        
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px 14px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
            background: #fafafa;
            box-sizing: border-box;
            max-width: 100%;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            border-color: #00695c;
            outline: none;
            box-shadow: 0 0 0 4px rgba(0,105,92,0.1);
            background: white;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            white-space: nowrap;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00695c, #26a69a);
            color: white;
            box-shadow: 0 4px 20px rgba(0,105,92,0.25);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(0,105,92,0.35);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            box-shadow: 0 4px 20px rgba(16,185,129,0.25);
        }
        
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(16,185,129,0.35);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            box-shadow: 0 4px 20px rgba(239,68,68,0.2);
        }
        
        .btn-danger:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(239,68,68,0.3);
        }
        
        .btn-secondary {
            background: #f3f4f6;
            color: #1a1a2e;
        }
        
        .btn-secondary:hover {
            background: #e5e7eb;
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            box-shadow: 0 4px 20px rgba(245,158,11,0.25);
        }
        
        .btn-warning:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(245,158,11,0.35);
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .form-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
            width: 100%;
        }
        
        .user-settings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
            width: 100%;
        }
        
        .user-settings-header .user-info h2 {
            font-size: 20px;
            color: #1a1a2e;
            word-break: break-word;
        }
        
        .user-settings-header .user-info .email {
            font-size: 14px;
            color: #6b7280;
            word-break: break-all;
        }
        
        .config-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-top: 15px;
            width: 100%;
        }
        
        .config-item {
            background: #ffffff;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #00695c;
            transition: all 0.3s;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.05);
            border-left-width: 4px;
            width: 100%;
            overflow: visible;
        }
        
        .config-item:hover {
            box-shadow: 0 8px 32px rgba(0,0,0,0.10);
            transform: translateX(5px);
        }
        
        .config-item .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 10px;
            width: 100%;
        }
        
        .config-item .item-id {
            font-size: 13px;
            font-weight: 600;
            color: #00695c;
        }
        
        .config-item .item-status {
            padding: 3px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: white;
            white-space: nowrap;
        }
        
        /* ===== ENTRY DISPLAY STYLES - UPDATED FOR OBJECT FIELDS ===== */
        .entry-details {
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
            margin: 10px 0;
        }
        
        .entry-field-group {
            border-radius: 8px;
            overflow: visible;
            width: 100%;
        }
        
        .entry-field-group.individual-field {
            background: #f8fafc;
            padding: 10px 14px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        .entry-field-group.object-field {
            background: #f0fdf4;
            padding: 12px 14px;
            border: 1px solid #a7f3d0;
            border-radius: 8px;
        }
        
        .field-label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 4px;
        }
        
        .field-value {
            font-size: 14px;
            color: #1a1a2e;
            word-break: break-word;
            max-height: 120px;
            overflow-y: auto;
            padding-right: 5px;
        }
        
        .field-value::-webkit-scrollbar {
            width: 4px;
        }
        
        .field-value::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .field-value::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 4px;
        }
        
        .field-value::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        .sub-fields-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 8px;
            padding-left: 8px;
            border-left: 2px solid #a7f3d0;
        }
        
        .sub-field-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
            padding: 6px 10px;
            background: #ffffff;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
        }
        
        .sub-field-item .sub-label {
            font-size: 11px;
            font-weight: 500;
            color: #6b7280;
        }
        
        .sub-field-item .sub-value {
            font-size: 13px;
            color: #1a1a2e;
            word-break: break-word;
            max-height: 80px;
            overflow-y: auto;
        }
        
        .sub-field-item .sub-value::-webkit-scrollbar {
            width: 3px;
        }
        
        .sub-field-item .sub-value::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 3px;
        }
        
        .sub-field-item .sub-value::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 3px;
        }
        
        .object-label {
            font-size: 13px;
            font-weight: 600;
            color: #00695c;
            margin-bottom: 6px;
        }
        
        .entry-field-group .field-value {
            max-height: 120px;
            overflow-y: auto;
            padding-right: 5px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar {
            width: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        /* Fallback for older browsers */
        .config-item .item-details .detail-label {
            font-size: 11px;
            color: #6b7280;
            text-transform: uppercase;
            font-weight: 600;
            flex-shrink: 0;
            padding-bottom: 2px;
        }
        
        .config-item .item-details .detail-value {
            font-size: 13px;
            color: #1a1a2e;
            word-break: break-word;
            max-height: 80px;
            overflow-y: auto;
        }
        
        .config-item .item-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            flex-wrap: wrap;
            width: 100%;
        }
        
        .config-item .item-actions .btn {
            padding: 6px 14px;
            font-size: 12px;
        }
        
        .config-item .item-actions form {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .config-item .status-select {
            padding: 4px 8px;
            border: 2px solid #e5e7eb;
            border-radius: 6px;
            font-size: 12px;
            background: #fafafa;
            cursor: pointer;
        }
        
        .config-item .status-select:focus {
            border-color: #00695c;
            outline: none;
        }
        
        .entry-user-tag {
            font-size: 12px;
            color: #00695c;
            background: #e0f2f1;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: 500;
        }
        
        .notification {
            padding: 12px 18px;
            border-radius: 10px;
            margin-bottom: 15px;
            font-size: 14px;
            width: 100%;
            box-sizing: border-box;
            word-break: break-word;
        }
        
        .notification.success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        
        .notification.error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }
        
        .datetime-group {
            width: 100%;
            box-sizing: border-box;
        }
        
        .datetime-group .date-input {
            width: 100%;
            padding: 10px 14px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            background: #fafafa;
            box-sizing: border-box;
        }
        
        .datetime-group .date-input:focus {
            border-color: #00695c;
            outline: none;
            box-shadow: 0 0 0 4px rgba(0,105,92,0.1);
            background: white;
        }
        
        .datetime-group .time-group {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
            margin-top: 8px;
            width: 100%;
        }
        
        .datetime-group .time-group input[type="number"],
        .datetime-group .time-group select {
            padding: 8px 10px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            background: #fafafa;
            min-width: 50px;
        }
        
        .datetime-group .time-group input[type="number"] {
            width: 60px;
        }
        
        .datetime-group .time-group select {
            width: 70px;
        }
        
        .datetime-group .time-group input[type="number"]:focus,
        .datetime-group .time-group select:focus {
            border-color: #00695c;
            outline: none;
        }
        
        .value-tag {
            display: inline-block;
            background: #e5e7eb;
            padding: 4px 12px;
            border-radius: 12px;
            margin: 3px;
            font-size: 13px;
        }
        
        .value-tag .remove-value {
            cursor: pointer;
            color: #ef4444;
            margin-left: 6px;
        }
        
        .sub-field-group {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 12px;
            background: #fafafa;
            position: relative;
        }
        
        .remove-sub-field {
            color: #ef4444;
            cursor: pointer;
            float: right;
            font-size: 18px;
            background: none;
            border: none;
            padding: 0 5px;
        }
        
        /* ================================================================
           CUSTOM DIALOG - FIXED FOR ALL SCREEN SIZES
           ================================================================ */
        .custom-dialog-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100vw;
            height: 100vh;
            min-height: 100vh;
            background: rgba(0, 0, 0, 0.6);
            z-index: 999999 !important;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
            padding: 20px;
            box-sizing: border-box;
            overflow: hidden;
        }
        
        .custom-dialog-overlay.active {
            display: flex !important;
            opacity: 1;
            visibility: visible;
        }
        
        .custom-dialog-box {
            background: #ffffff;
            border-radius: 16px;
            padding: 30px;
            max-width: 650px;
            width: 100%;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
            animation: dialogSlideIn 0.3s ease;
            position: relative;
            margin: 20px;
            box-sizing: border-box;
            display: block !important;
            visibility: visible !important;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        @keyframes dialogSlideIn {
            from {
                transform: translateY(-40px) scale(0.95);
                opacity: 0;
            }
            to {
                transform: translateY(0) scale(1);
                opacity: 1;
            }
        }
        
        .custom-dialog-box .dialog-title {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #1a1a2e;
            display: block;
        }
        
        .custom-dialog-box .dialog-message {
            font-size: 16px;
            color: #6b7280;
            margin-bottom: 20px;
            line-height: 1.6;
            display: block;
        }
        
        .custom-dialog-box .dialog-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            flex-wrap: wrap;
            width: 100%;
            margin-top: 10px;
        }
        
        .custom-dialog-box .dialog-buttons .btn {
            min-width: 80px;
        }
        
        .custom-dialog-box .dialog-buttons .btn-confirm {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
        }
        
        .custom-dialog-box .dialog-buttons .btn-confirm:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
        }
        
        .custom-dialog-box .dialog-content-area {
            background: #f8fafc;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #e5e7eb;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 13px;
            white-space: pre-wrap;
            word-break: break-all;
            width: 100%;
            box-sizing: border-box;
        }
        
        .custom-dialog-box .dialog-content-area:focus {
            outline: 2px solid #00695c;
            outline-offset: 2px;
        }
        
        /* Scrollbar for dialog content */
        .custom-dialog-box .dialog-content-area::-webkit-scrollbar {
            width: 6px;
        }
        
        .custom-dialog-box .dialog-content-area::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .custom-dialog-box .dialog-content-area::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 4px;
        }
        
        /* Dialog content wrapper */
        #dialogContent {
            margin-bottom: 15px;
            display: block;
            width: 100%;
        }
        
        #dialogContent > * {
            display: block;
            width: 100%;
        }
        
        /* ===== USER SEARCH MODAL ===== */
        .user-search-modal .custom-dialog-box {
            max-width: 600px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            padding: 0;
            overflow: hidden;
        }
        
        .user-search-modal .dialog-header {
            padding: 20px 25px 15px;
            border-bottom: 1px solid #e5e7eb;
            flex-shrink: 0;
            background: white;
            border-radius: 16px 16px 0 0;
        }
        
        .user-search-modal .dialog-header h2 {
            font-size: 20px;
            color: #1a1a2e;
            margin-bottom: 12px;
        }
        
        .user-search-modal .dialog-header .search-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            font-size: 16px;
            background: #fafafa;
            transition: all 0.3s;
        }
        
        .user-search-modal .dialog-header .search-input:focus {
            border-color: #00695c;
            outline: none;
            box-shadow: 0 0 0 4px rgba(0,105,92,0.1);
            background: white;
        }
        
        .user-search-modal .dialog-body {
            flex: 1;
            overflow-y: auto;
            padding: 15px 25px 25px;
        }
        
        .user-search-modal .dialog-body::-webkit-scrollbar {
            width: 6px;
        }
        
        .user-search-modal .dialog-body::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.02);
            border-radius: 10px;
        }
        
        .user-search-modal .dialog-body::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #00695c, #26a69a);
            border-radius: 10px;
        }
        
        .user-search-modal .user-search-item {
            padding: 12px 16px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 4px;
            border: 1px solid transparent;
        }
        
        .user-search-modal .user-search-item:hover {
            background: #f3f4f6;
            border-color: #e5e7eb;
        }
        
        .user-search-modal .user-search-item .user-name {
            font-weight: 500;
            color: #1a1a2e;
            font-size: 15px;
        }
        
        .user-search-modal .user-search-item .user-email {
            font-size: 13px;
            color: #6b7280;
        }
        
        .user-search-modal .dialog-footer {
            padding: 15px 25px 20px;
            border-top: 1px solid #e5e7eb;
            flex-shrink: 0;
            display: flex;
            justify-content: flex-end;
            background: white;
            border-radius: 0 0 16px 16px;
        }
        
        
        .copy-btn {
            background: none;
            border: 1px solid #d1d5db;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            color: #6b7280;
        }
        
        .copy-btn:hover {
            background: #f3f4f6;
            border-color: #00695c;
            color: #00695c;
        }
        
        /* ===== TOGGLE SWITCH ===== */
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 40px;
            height: 22px;
            flex-shrink: 0;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 22px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        
        .toggle-switch input:checked + .toggle-slider {
            background-color: #00695c;
        }
        
        .toggle-switch input:checked + .toggle-slider:before {
            transform: translateX(18px);
        }
        
        .tab-editor-item {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 12px;
            background: #fafafa;
        }
        
        .tab-editor-item .tab-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .tab-editor-item .tab-header .tab-title {
            font-weight: 600;
            color: #1a1a2e;
        }
        
        .field-toggle-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            margin: 2px 0;
            border-radius: 6px;
            background: #f3f4f6;
        }
        
        .field-toggle-item:hover {
            background: #e5e7eb;
        }
        
        .field-toggle-item .field-name {
            font-size: 13px;
            color: #1a1a2e;
        }
        
        /* ===== SCROLLABLE VALUE ===== */
        .scrollable-value {
            max-height: 80px;
            overflow-y: auto;
            padding-right: 5px;
            word-break: break-word;
            display: block;
            width: 100%;
        }
        
        .scrollable-value::-webkit-scrollbar {
            width: 4px;
        }
        
        .scrollable-value::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .scrollable-value::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 4px;
        }
        
        .scrollable-value::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        /* ================================================================
           RESPONSIVE MEDIA QUERIES
           ================================================================ */
        @media (max-width: 1024px) {
            .two-col {
                grid-template-columns: 250px 1fr;
                gap: 15px;
            }
        }
        
        @media (max-width: 768px) {
            .two-col {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            
            .sidebar {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .content-area {
                padding: 15px;
            }
            
            .main-header {
                padding: 10px 15px;
                min-height: 55px;
            }
            
            .main-header h1 {
                font-size: 16px;
            }
            
            .scroll-body {
                padding: 0 10px 30px !important;
                padding-top: 0 !important;
            }
            
            .dashboard-tabs {
                overflow-x: auto;
                flex-wrap: nowrap;
                -webkit-overflow-scrolling: touch;
            }
            
            .dashboard-tab-btn {
                padding: 8px 14px;
                font-size: 13px;
                white-space: nowrap;
                min-height: 42px;
            }
            
            .user-config-tabs {
                overflow-x: auto;
                flex-wrap: nowrap;
                -webkit-overflow-scrolling: touch;
            }
            
            .user-config-tab-btn {
                padding: 8px 14px;
                font-size: 13px;
                white-space: nowrap;
                min-height: 42px;
            }
            
            .dynamic-sub-tabs {
                overflow-x: auto;
                flex-wrap: nowrap;
                -webkit-overflow-scrolling: touch;
            }
            
            .dynamic-sub-tab-btn {
                padding: 6px 12px;
                font-size: 12px;
                white-space: nowrap;
                min-height: 36px;
            }
            
            .config-item {
                padding: 14px;
            }
            
            .config-item .item-details {
                grid-template-columns: 1fr;
            }
            
            .custom-dialog-box {
                padding: 20px;
                margin: 10px;
                max-width: 95%;
                max-height: 90vh;
            }
            
            .user-search-modal .custom-dialog-box {
                max-width: 95%;
                max-height: 90%;
            }
            
            .user-search-modal .dialog-header {
                padding: 15px 18px 12px;
            }
            
            .user-search-modal .dialog-body {
                padding: 12px 18px 18px;
            }
            
            .create-user-form {
                padding: 15px;
            }
            
            .btn {
                padding: 8px 16px;
                font-size: 13px;
            }
            
            .form-actions {
                flex-direction: column;
            }
            
            .form-actions .btn {
                width: 100%;
            }
            
            .config-item .item-actions {
                flex-direction: column;
                align-items: stretch;
            }
            
            .config-item .item-actions form {
                width: 100%;
            }
            
            .config-item .item-actions .btn {
                width: 100%;
                justify-content: center;
            }
            
            .config-item .status-select {
                width: 100%;
            }
            
            .datetime-group .time-group {
                flex-wrap: wrap;
            }
            
            .datetime-group .time-group input[type="number"] {
                width: 50px;
            }
            
            .datetime-group .time-group select {
                width: 60px;
            }
        }
        
        @media (max-width: 480px) {
            .main-header {
                padding: 8px 12px;
                min-height: 50px;
            }
            
            .main-header h1 {
                font-size: 14px;
            }
            
            .debug-btn {
                padding: 4px 10px;
                font-size: 12px;
            }
            
            .content-area {
                padding: 12px;
            }
            
            .sidebar {
                padding: 12px;
            }
            
            .dashboard-tab-btn {
                padding: 6px 10px;
                font-size: 12px;
                min-height: 38px;
            }
            
            .user-config-tab-btn {
                padding: 6px 10px;
                font-size: 12px;
                min-height: 38px;
            }
            
            .dynamic-sub-tab-btn {
                padding: 5px 10px;
                font-size: 11px;
                min-height: 34px;
            }
            
            .config-item {
                padding: 12px;
            }
            
            .config-item .item-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .custom-dialog-box {
                padding: 15px;
                max-width: 98%;
                max-height: 95vh;
                margin: 10px;
            }
            
            .custom-dialog-box .dialog-title {
                font-size: 18px;
            }
            
            .create-user-form {
                padding: 12px;
            }
            
            .create-user-form input {
                padding: 10px 14px;
                font-size: 14px;
            }
            
            .form-group input,
            .form-group select,
            .form-group textarea {
                padding: 8px 12px;
                font-size: 14px;
            }
            
            .btn {
                padding: 8px 14px;
                font-size: 12px;
            }
            
            .btn-sm {
                padding: 4px 10px;
                font-size: 11px;
            }
            
            .user-settings-header .user-info h2 {
                font-size: 18px;
            }
            
            .user-search-modal .custom-dialog-box {
                max-width: 98%;
                max-height: 95%;
            }
        }
        
        .default-value-wrapper {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .default-value-wrapper input {
            width: 100%;
        }
        
        .field-with-default {
            width: 100%;
        }
        
        /* ===== COPY BUTTON STYLES ===== */
        .entry-field-group .field-value {
            max-height: 120px;
            overflow-y: auto;
            padding-right: 5px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar {
            width: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-thumb {
            background: #00695c;
            border-radius: 4px;
        }
        
        .entry-field-group .field-value::-webkit-scrollbar-thumb:hover {
            background: #004d40;
        }
        
        /* Individual field copy button */
        .entry-field-group.individual-field {
            background: #f8fafc;
            padding: 10px 14px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        /* Object field copy button */
        .entry-field-group.object-field {
            background: #f0fdf4;
            padding: 12px 14px;
            border: 1px solid #a7f3d0;
            border-radius: 8px;
        }
        
        /* Copy button styling */
        .btn-secondary.btn-sm {
            padding: 4px 10px;
            font-size: 11px;
            background: #e5e7eb;
            color: #1a1a2e;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-secondary.btn-sm:hover {
            background: #d1d5db;
            transform: translateY(-1px);
        }
        
        /* ================================================================
           DIALOG FIXES FOR LARGE SCREENS - ENSURES VISIBILITY
           ================================================================ */
        .custom-dialog-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100vw;
            height: 100vh;
            min-height: 100vh;
            background: rgba(0, 0, 0, 0.6);
            z-index: 999999 !important;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
            padding: 20px;
            box-sizing: border-box;
            overflow: hidden;
        }
        
        .custom-dialog-overlay.active {
            display: flex !important;
            opacity: 1;
            visibility: visible;
        }
        
        /* Force dialog to be on top of everything */
        .custom-dialog-overlay,
        .custom-dialog-overlay * {
            z-index: 999999 !important;
        }
        
        /* Ensure dialog box is visible on all screen sizes */
        .custom-dialog-box {
            background: #ffffff;
            border-radius: 16px;
            padding: 30px;
            max-width: 650px;
            width: 100%;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
            animation: dialogSlideIn 0.3s ease;
            position: relative;
            margin: 20px;
            box-sizing: border-box;
            display: block !important;
            visibility: visible !important;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Fix for very large screens */
        @media (min-width: 1600px) {
            .custom-dialog-box {
                max-width: 700px;
                padding: 40px;
            }
        }
        
        /* Fix for very small screens */
        @media (max-width: 400px) {
            .custom-dialog-box {
                padding: 12px;
                margin: 5px;
            }
            
            .custom-dialog-box .dialog-title {
                font-size: 16px;
            }
            
            .custom-dialog-box .dialog-message {
                font-size: 14px;
            }
            
            .custom-dialog-box .dialog-buttons .btn {
                font-size: 12px;
                padding: 6px 12px;
                min-width: 60px;
            }
        }
    /* ===== TRANSCRIPT DETECTION STYLES ===== */
    .transcript-indicator {
        margin-top: 8px;
        padding: 8px 12px;
        background: #d1fae5;
        border-radius: 8px;
        border-left: 4px solid #00695c;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .transcript-indicator .indicator-text {
        color: #065f46;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .transcript-indicator .btn-view {
        padding: 4px 12px;
        font-size: 12px;
    }

    /* Transcript viewer modal adjustments */
    #transcriptConversionResult {
        margin-top: 15px;
    }

    #transcriptConversionResult .result-box {
        background: #f0fdf4;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #a7f3d0;
    }

    #transcriptConversionResult .result-box .result-title {
        color: #065f46;
        font-weight: 600;
        margin-bottom: 8px;
    }

    #transcriptConversionResult .result-box .result-stats {
        font-size: 13px;
        color: #065f46;
    }
    /* Toggle switch styles - ensure these exist */
    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 40px;
        height: 22px;
        flex-shrink: 0;
    }

    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .toggle-slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 22px;
    }

    .toggle-slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
    }

    .toggle-switch input:checked + .toggle-slider {
        background-color: #00695c;
    }

    .toggle-switch input:checked + .toggle-slider:before {
        transform: translateX(18px);
    }
/* ===== REFINED DYNAMIC TABS UI (scoped, responsive, predictable) ===== */
#dynamicTabsEditor{--dt-ink:#172033;--dt-muted:#687386;--dt-line:#dce3ec;--dt-soft:#f6f8fb;--dt-teal:#087f75;--dt-teal-dark:#075e57;--dt-red:#b42318;width:100%;min-width:0;color:var(--dt-ink)}
#dynamicTabsEditor *{box-sizing:border-box}
#dynamicTabsEditor .dynamic-tabs-editor-header{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:22px 24px;margin:0 0 22px;border:1px solid #d8e7e5;border-radius:16px;background:linear-gradient(120deg,#f0fdfa 0%,#f8fbff 72%);box-shadow:0 5px 18px rgba(15,45,55,.045)}
#dynamicTabsEditor .dynamic-tabs-editor-header h3{font-size:22px;line-height:1.25;font-weight:750;letter-spacing:-.025em;color:#102a32;margin:0 0 7px}
#dynamicTabsEditor .dynamic-tabs-editor-header p{max-width:720px;color:#5c6d7c;font-size:13px;line-height:1.65;margin:0}
#dynamicTabsEditor .dynamic-tabs-editor-header .btn{flex:0 0 auto;min-height:42px;padding:10px 16px;border-radius:10px;font-weight:700;box-shadow:0 3px 8px rgba(8,127,117,.12)}
#dynamicTabsEditor .dynamic-tabs-editor-list{display:flex;flex-direction:column;gap:18px;counter-reset:main-tab;min-width:0}
#dynamicTabsEditor .tab-editor-item{position:relative;min-width:0;width:100%;margin:0;padding:0;overflow:hidden;border:1px solid var(--dt-line);border-radius:15px;background:#fff;box-shadow:0 4px 14px rgba(20,35,55,.045)}
#dynamicTabsEditor .root-tab-editor-item{counter-increment:main-tab;border-top:3px solid #087f75;border-left:1px solid var(--dt-line)}
#dynamicTabsEditor .root-tab-editor-item>.tab-editor-heading{padding:16px 18px;background:linear-gradient(180deg,#f7fcfb,#fff);border-bottom:1px solid #e5ecef}
#dynamicTabsEditor .root-tab-editor-item>.tab-editor-heading .tab-editor-kind:before{content:'MAIN TAB ' counter(main-tab);display:inline-flex;align-items:center;justify-content:center;margin-right:8px;padding:4px 8px;border-radius:6px;background:#d9f4ef;color:#075e57;font-size:10px;letter-spacing:.07em}
#dynamicTabsEditor .root-tab-editor-item>.tab-editor-heading .tab-editor-kind{font-size:0;color:transparent}
#dynamicTabsEditor .tab-editor-heading{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;min-width:0}
#dynamicTabsEditor .tab-editor-heading-copy{display:flex;flex:1 1 220px;min-width:0;flex-direction:column;gap:7px}
#dynamicTabsEditor .tab-editor-title{display:block;min-width:0;overflow-wrap:anywhere;font-size:16px;line-height:1.4;font-weight:750;color:#182638}
#dynamicTabsEditor .tab-editor-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap}
#dynamicTabsEditor .tab-editor-actions .btn{min-height:34px;padding:7px 11px;border-radius:8px;font-size:12px;font-weight:650}
#dynamicTabsEditor .tab-editor-actions .btn-danger{background:#fff5f4;color:#a32920;border:1px solid #f2c7c3}
#dynamicTabsEditor .tab-editor-actions .btn-danger:hover{background:#fee9e7}
#dynamicTabsEditor .tab-editor-actions .btn-secondary{background:#fff;color:#425166;border:1px solid #d8e0e9}
#dynamicTabsEditor .nested-tab-editor-body{display:block;padding:20px;min-width:0}
#dynamicTabsEditor .tab-editor-item .form-group{display:flex;flex-direction:column;gap:7px;margin:0 0 18px;min-width:0}
#dynamicTabsEditor .tab-editor-item .form-group>label{font-size:12px;font-weight:750;letter-spacing:.015em;color:#344256}
#dynamicTabsEditor .tab-editor-item .form-group input[type=text],#dynamicTabsEditor .tab-editor-item .form-group select,#dynamicTabsEditor .tab-editor-item .form-group textarea{display:block;width:100%;max-width:100%;min-width:0;min-height:42px;padding:10px 12px;border:1px solid #cfd8e3;border-radius:9px;background:#fff;color:#172033;font-size:14px!important;line-height:1.45;box-shadow:none;transition:border-color .15s,box-shadow .15s}
#dynamicTabsEditor .tab-editor-item .form-group textarea{min-height:82px;resize:vertical}
#dynamicTabsEditor .tab-editor-item .form-group input:focus,#dynamicTabsEditor .tab-editor-item .form-group select:focus,#dynamicTabsEditor .tab-editor-item .form-group textarea:focus{outline:none;border-color:#087f75;box-shadow:0 0 0 3px rgba(8,127,117,.12)}
#dynamicTabsEditor .tab-editor-help{margin:2px 0 0;padding:10px 12px;border-radius:8px;background:#f2f7fb;color:#5e6e81;font-size:12px;line-height:1.6}
#dynamicTabsEditor .tab-fields-toggle-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:12px;border:1px solid #e0e7ef;border-radius:11px;background:#f8fafc}
#dynamicTabsEditor .tab-field-option{display:flex;align-items:center;justify-content:space-between;gap:12px;min-width:0;min-height:44px;padding:10px 12px;border:1px solid #e0e6ed;border-radius:9px;background:#fff;cursor:pointer;transition:border-color .15s,background .15s}
#dynamicTabsEditor .tab-field-option:hover{border-color:#8dcfc5;background:#f7fffd}
#dynamicTabsEditor .tab-field-option input{flex:0 0 auto;width:17px;height:17px;margin:0;accent-color:#087f75}
#dynamicTabsEditor .tab-field-label{min-width:0;overflow-wrap:anywhere;font-size:12px;line-height:1.5;color:#344256}
#dynamicTabsEditor .tab-field-label small{display:block;margin-top:2px;color:#8490a0;font-size:10px}
#dynamicTabsEditor .tab-feature-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;padding:12px;border:1px solid #e0e7ef;border-radius:11px;background:#fbfcfe}
#dynamicTabsEditor .tab-feature-options label{display:flex;align-items:center;gap:8px;min-width:0;margin:0;padding:10px;border:1px solid #e6ebf1;border-radius:8px;background:#fff;color:#3f4d60;font-size:12px;line-height:1.45;cursor:pointer}
#dynamicTabsEditor .tab-feature-options input{flex:0 0 auto;accent-color:#087f75;width:16px;height:16px;margin:0}
#dynamicTabsEditor .nested-sub-tabs-container{margin:20px 0 0;padding:17px;border:1px solid #b8e4dc;border-radius:13px;background:#f2fbf9}
#dynamicTabsEditor .nested-sub-tabs-heading{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:0 0 14px;padding-bottom:13px;border-bottom:1px solid #d7eeea}
#dynamicTabsEditor .nested-sub-tabs-heading strong{display:block;color:#145b55;font-size:15px;font-weight:800}
#dynamicTabsEditor .nested-sub-tabs-heading p{margin:5px 0 0;color:#647b7a;font-size:12px;line-height:1.5}
#dynamicTabsEditor .nested-sub-tabs-heading .btn{min-height:36px;padding:8px 12px;border-radius:9px;font-weight:700}
#dynamicTabsEditor .nested-sub-tabs-list{display:flex;flex-direction:column;gap:12px;min-width:0}
#dynamicTabsEditor .sub-tab-editor-item{border:1px solid #d8e2eb;border-left:4px solid #7b8da4;border-radius:11px;background:#fff;box-shadow:none}
#dynamicTabsEditor .sub-tab-editor-item>.tab-editor-heading{padding:13px 15px;background:#f7f9fc;border-bottom:1px solid #e7edf3}
#dynamicTabsEditor .sub-tab-editor-item .tab-editor-kind{display:inline-flex;align-self:flex-start;padding:4px 7px;border-radius:5px;background:#e8eef5;color:#53677e;font-size:10px;font-weight:800;letter-spacing:.08em}
#dynamicTabsEditor .sub-tab-editor-item .tab-editor-title{font-size:14px}
#dynamicTabsEditor .sub-tab-editor-item .nested-tab-editor-body{padding:16px}
#dynamicTabsEditor .nested-sub-tabs-empty{margin:0;padding:16px;border:1px dashed #b8d9d4;border-radius:9px;background:rgba(255,255,255,.7);color:#637c79;text-align:center;font-size:12px;line-height:1.5}
#dynamicTabsEditor .tab-editor-empty-fields{margin:0;padding:13px;border:1px dashed #d1dbe5;border-radius:9px;background:#fff;color:#718096;font-size:12px;line-height:1.5}
#dynamicTabsEditor .tab-editor-empty-state{margin:0 0 16px;padding:34px 20px;border:1px dashed #cbd7e2;border-radius:14px;background:#fafcff;color:#6b7788;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center}
#dynamicTabsEditor .tab-editor-empty-state strong{font-size:15px;color:#27364a}
#dynamicTabsEditor .dynamic-tabs-save-bar{position:sticky;bottom:0;z-index:20;display:flex;justify-content:flex-end;gap:12px;margin:22px -2px 0;padding:14px 2px 3px;background:linear-gradient(180deg,rgba(255,255,255,0),#fff 28%)}
#dynamicTabsEditor .dynamic-tabs-save-bar .btn{min-height:44px;padding:11px 20px;border-radius:10px;font-size:14px;font-weight:800;box-shadow:0 4px 12px rgba(8,127,117,.16)}
#dynamicTabsEditor .btn:focus-visible{outline:3px solid rgba(8,127,117,.25);outline-offset:2px}
/* Nested project tabs: clearly separated parent and child navigation/content */
#newProjectSubTabs{display:flex;flex-wrap:wrap;gap:8px;padding:10px;margin:0 0 18px;border:1px solid #dce5ed;border-radius:12px;background:#f7f9fc;white-space:normal;overflow:visible}
#newProjectSubTabs .dynamic-sub-tab-btn{min-height:40px;margin:0;padding:9px 14px;border:1px solid #d9e2eb;border-radius:9px;background:#fff;color:#46566b;font-size:13px;font-weight:650;white-space:normal}
#newProjectSubTabs .dynamic-sub-tab-btn.active{border-color:#087f75;background:#e5f7f3;color:#075e57;box-shadow:inset 0 0 0 1px rgba(8,127,117,.08)}
#user_tab_add_entry .dynamic-sub-tab-content{padding:18px;border:1px solid #dce5ed;border-radius:13px;background:#fff}
#user_tab_add_entry .nested-project-tabs{padding:14px;border:1px solid #d5e9e5;border-radius:12px;background:#f8fcfb}
#user_tab_add_entry .nested-project-tabs .dynamic-sub-tabs{display:flex;flex-wrap:wrap;gap:7px;padding:0 0 12px;border-bottom:1px solid #dfe8ec;overflow:visible;white-space:normal}
#user_tab_add_entry .nested-project-tabs .nested-child-btn{margin:0;padding:8px 12px;border:1px solid #d8e2eb;border-radius:8px;background:#fff;color:#526176;font-size:12px;font-weight:650;white-space:normal}
#user_tab_add_entry .nested-project-tabs .nested-child-btn.active{border-color:#8acfc4;background:#e7f8f4;color:#075e57}
#user_tab_add_entry .nested-child-content{padding:16px 4px 4px}
@media(max-width:760px){#dynamicTabsEditor .dynamic-tabs-editor-header{align-items:stretch;flex-direction:column;padding:17px}#dynamicTabsEditor .dynamic-tabs-editor-header .btn{width:100%}#dynamicTabsEditor .nested-tab-editor-body{padding:14px}#dynamicTabsEditor .root-tab-editor-item>.tab-editor-heading{padding:13px}#dynamicTabsEditor .tab-editor-actions{width:100%;justify-content:flex-start}#dynamicTabsEditor .tab-editor-actions .btn{flex:1 1 auto}#dynamicTabsEditor .tab-fields-toggle-list{grid-template-columns:minmax(0,1fr)}#dynamicTabsEditor .tab-feature-options{grid-template-columns:minmax(0,1fr)}#dynamicTabsEditor .nested-sub-tabs-container{padding:12px}#dynamicTabsEditor .nested-sub-tabs-heading{align-items:stretch;flex-direction:column}#dynamicTabsEditor .nested-sub-tabs-heading .btn{width:100%}#dynamicTabsEditor .dynamic-tabs-save-bar .btn{width:100%}#user_tab_add_entry .dynamic-sub-tab-content{padding:12px}}
@media(prefers-reduced-motion:reduce){#dynamicTabsEditor *,#newProjectSubTabs *{transition:none!important;scroll-behavior:auto!important}}

/* ===== SINGLE-WINNER STICKY NAVIGATION =====
   Navigation hand-off:
   1) The hardcoded account tabs (New Project, Pending, Completed, Aborted, etc.)
      stay at the top while they are the only navigation row in use.
   2) When the dynamic main-tab row reaches the top, it takes over and the
      hardcoded row is released to scroll away.
   3) When a nested row reaches the top, it takes over and the dynamic main row
      is released. Scrolling upward restores the previous row naturally.
   ========================================================== */
.content-area {
    overflow: visible !important;
    min-height: 0;
}

/* Sticky navigation stacking order: default 800, dynamic main 900, nested child 1000. */
.user-config-tabs {
    position: sticky;
    top: 0;
    z-index: 800;
    isolation: isolate;
    background: rgba(255, 255, 255, .98);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 14px rgba(15, 35, 55, .09);
}

/* Keep the default row sticky, but always beneath both dynamic navigation rows. */
.user-config-tabs.default-nav-released {
    position: sticky !important;
    top: 0 !important;
    z-index: 800 !important;
}

/* The main dynamic row is sticky until a nested child row arrives. */
#user_tab_add_entry #newProjectSubTabs {
    position: sticky;
    top: 0;
    z-index: 900;
    isolation: isolate;
    background: rgba(247, 249, 252, .99);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    box-shadow: 0 5px 16px rgba(15, 35, 55, .10);
    border-color: #cbd9e5;
    scroll-margin-top: 0;
}

/* The main row remains sticky underneath the nested child row. */
#user_tab_add_entry.child-nav-priority #newProjectSubTabs {
    position: sticky !important;
    top: 0 !important;
    z-index: 900 !important;
}

/* Child row takes over the entire dynamic-content width while stuck. */
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    position: sticky;
    top: 0;
    z-index: 1000;
    isolation: isolate;
    width: calc(100% + 64px);
    max-width: none;
    margin-left: -32px;
    margin-right: -32px;
    padding: 10px 32px 12px !important;
    background: rgba(248, 252, 251, .99);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
    box-shadow: 0 5px 16px rgba(15, 35, 55, .12);
    border-bottom: 1px solid #cbdedb;
    box-sizing: border-box;
}

#user_tab_add_entry.child-nav-priority #newProjectSubTabs,
#user_tab_add_entry.child-nav-priority .nested-project-tabs > .dynamic-sub-tabs {
    transition: box-shadow .18s ease, background-color .18s ease;
}

.custom-dialog-overlay { z-index: 999999 !important; }

@media (max-width: 760px) {
    #user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
        width: calc(100% + 52px);
        margin-left: -26px;
        margin-right: -26px;
        padding: 9px 26px 11px !important;
        gap: 6px;
    }
    #user_tab_add_entry #newProjectSubTabs {
        gap: 6px;
        padding: 8px;
        border-radius: 0 0 11px 11px;
    }
}

@media (prefers-reduced-motion: reduce) {
    .user-config-tabs,
    #user_tab_add_entry #newProjectSubTabs,
    #user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
        transition: none !important;
    }
}


        /* Dynamic-tab editor controls */
        .dynamic-tabs-save-bar { position: sticky; bottom: 0; z-index: 50; background: rgba(255,255,255,.97); border-top: 1px solid #e2e8f0; padding: 12px; margin-top: 16px; }
        .display-tab-toggle { display:inline-flex; align-items:center; gap:10px; cursor:pointer; padding:8px 10px; border:1px solid #cbd5e1; border-radius:9px; background:#f8fafc; }
        .display-tab-toggle input { width:18px; height:18px; accent-color:#0f766e; }
        .display-tab-state { font-size:12px; color:#334155; }
        #user_tab_dynamic_fields > div > div[style*="display:flex"] { position:sticky; bottom:0; z-index:40; background:rgba(255,255,255,.97); padding:12px 0; border-top:1px solid #e2e8f0; }
        .dynamic-tabs-editor-list { padding-bottom:70px; }

        .dynamic-tabs-save-bar { position: sticky; bottom: 0; z-index: 50; background: rgba(255,255,255,.97); border-top: 1px solid #e2e8f0; padding: 12px; margin-top: 16px; }
        .display-tab-toggle { display:inline-flex; align-items:center; gap:10px; cursor:pointer; padding:8px 10px; border:1px solid #cbd5e1; border-radius:9px; background:#f8fafc; }
        .display-tab-toggle input { width:18px; height:18px; accent-color:#0f766e; }
        .display-tab-state { font-size:12px; color:#334155; }
        #user_tab_dynamic_fields > div > div[style*="display:flex"] { position:sticky; bottom:0; z-index:40; background:rgba(255,255,255,.97); padding:12px 0; border-top:1px solid #e2e8f0; }
        .dynamic-tabs-editor-list { padding-bottom:70px; }

/* ===== FINAL DESIGN RULES: full outlines only, no directional accent borders ===== */
#dynamicTabsEditor .root-tab-editor-item,
#dynamicTabsEditor .sub-tab-editor-item,
#dynamicTabsEditor .root-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .sub-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .nested-sub-tabs-heading,
#dynamicTabsEditor .nested-project-tabs .dynamic-sub-tabs,
#dynamicTabsEditor .dynamic-tabs-save-bar,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs .dynamic-sub-tabs,
#user_tab_submit_tabs .submit-tabs-save-bar,
#user_tab_dynamic_fields .account-dynamic-fields-add-bar {
    border-top: 0 !important;
    border-left: 0 !important;
    border-right: 0 !important;
    border-bottom: 0 !important;
}
#dynamicTabsEditor .root-tab-editor-item,
#dynamicTabsEditor .sub-tab-editor-item,
#dynamicTabsEditor .root-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .sub-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .nested-sub-tabs-heading,
#dynamicTabsEditor .dynamic-tabs-save-bar,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs .dynamic-sub-tabs,
#user_tab_submit_tabs .submit-tabs-save-bar,
#user_tab_dynamic_fields .account-dynamic-fields-add-bar {
    border: 1px solid #dce5ed !important;
}
#dynamicTabsEditor .root-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .sub-tab-editor-item > .tab-editor-heading,
#dynamicTabsEditor .nested-sub-tabs-heading {
    border-radius: 12px;
}
#dynamicTabsEditor .root-tab-editor-item { border: 1px solid var(--dt-line) !important; }
#dynamicTabsEditor .sub-tab-editor-item { border: 1px solid #d8e2eb !important; }
#dynamicTabsEditor .dynamic-tabs-save-bar {
    position: sticky !important; bottom: 0; z-index: 100;
    margin-top: 18px; padding: 12px;
    background: rgba(255,255,255,.98);
    box-shadow: 0 -8px 18px rgba(15,23,42,.08);
    border-radius: 12px;
}
.content-area { overflow: visible !important; }
#user_tab_submit_tabs { overflow: visible !important; }
#user_tab_submit_tabs #submitTabsEditor { padding-bottom: 92px; }
#user_tab_submit_tabs .submit-tabs-save-bar {
    position: sticky; bottom: 0; z-index: 100;
    display: flex; justify-content: flex-end;
    margin: 14px 0 0; padding: 12px;
    background: rgba(255,255,255,.98);
    box-shadow: 0 -8px 18px rgba(15,23,42,.08);
    border-radius: 12px;
}
#user_tab_submit_tabs .submit-tabs-save-bar .btn { min-height: 44px; }
#user_tab_dynamic_fields { overflow: visible !important; }
#user_tab_dynamic_fields #userGlobalDynamicFieldsList { padding-bottom: 92px; }
#user_tab_dynamic_fields .account-dynamic-fields-add-bar {
    position: sticky; bottom: 0; z-index: 100;
    display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap;
    margin-top: 12px; padding: 12px;
    background: rgba(255,255,255,.98);
    box-shadow: 0 -8px 18px rgba(15,23,42,.08);
    border-radius: 12px;
}
.account-dynamic-field-card {
    display: block; width: 100%; margin: 0 0 12px; padding: 0;
    border: 1px solid #dce3ec; border-radius: 12px;
    background: #fff; box-shadow: 0 3px 10px rgba(15,23,42,.04);
    cursor: pointer; overflow: hidden; transition: background .15s, box-shadow .15s;
}
.account-dynamic-field-card:hover { background: #fbfdfd; box-shadow: 0 5px 14px rgba(15,23,42,.07); }
.account-dynamic-field-card:focus-visible { outline: 2px solid #087f75; outline-offset: 2px; }
.account-dynamic-field-heading {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 15px; min-width: 0;
}
.account-dynamic-field-title-wrap { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.account-dynamic-field-title { color: #1a1a2e; overflow-wrap: anywhere; }
.account-dynamic-field-key { color: #6b7280; font-size: 12px; overflow-wrap: anywhere; }
.account-dynamic-field-heading-side { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; }
.account-dynamic-field-type { font-size: 11px; color: #475569; background: #eef2f7; padding: 5px 9px; border-radius: 999px; }
.account-dynamic-field-chevron { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: 1px solid #dce3ec; border-radius: 8px; color: #334155; font-weight: 700; }
.account-dynamic-field-details { padding: 14px 15px 15px; border: 1px solid #e5eaf0; border-radius: 10px; margin: 0 12px 12px; background: #f8fafc; cursor: default; }
.account-dynamic-field-details[hidden] { display: none !important; }
.account-dynamic-field-info { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 14px; color: #64748b; font-size: 13px; overflow-wrap: anywhere; }
.account-dynamic-subfield { grid-column: 1 / -1; margin-left: 8px; font-size: 12px; color: #64748b; }
.account-dynamic-field-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; padding: 12px 0 0; border: 1px solid #e5eaf0; border-radius: 9px; }
@media (max-width: 640px) {
    #user_tab_submit_tabs .submit-tabs-save-bar .btn,
    #user_tab_dynamic_fields .account-dynamic-fields-add-bar .btn { width: 100%; }
    #user_tab_submit_tabs .submit-tabs-save-bar,
    #user_tab_dynamic_fields .account-dynamic-fields-add-bar { justify-content: stretch; }
    .account-dynamic-field-info { grid-template-columns: minmax(0,1fr); }
    .account-dynamic-field-heading { align-items: flex-start; }
    .account-dynamic-field-heading-side { gap: 6px; }
}


/* ===== STICKY ACTIONS: ONLY THE BUTTONS FLOAT; THE WRAPPER IS CLICK-THROUGH ===== */
#dynamicTabsEditor .dynamic-tabs-save-bar,
.dynamic-tabs-save-bar,
#user_tab_submit_tabs .submit-tabs-save-bar,
#user_tab_dynamic_fields .account-dynamic-fields-add-bar {
    position: sticky !important;
    bottom: 0 !important;
    z-index: 100 !important;
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    gap: 10px !important;
    flex-wrap: wrap !important;
    width: 100% !important;
    min-height: 0 !important;
    margin: 12px 0 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    pointer-events: none !important;
}

/* The invisible sticky area must never block controls beneath it. */
#dynamicTabsEditor .dynamic-tabs-save-bar > *,
.dynamic-tabs-save-bar > *,
#user_tab_submit_tabs .submit-tabs-save-bar > *,
#user_tab_dynamic_fields .account-dynamic-fields-add-bar > * {
    pointer-events: auto !important;
    flex: 0 0 auto;
}

/* Keep only the actual controls visible and interactive—not a white card. */
#dynamicTabsEditor .dynamic-tabs-save-bar .btn,
.dynamic-tabs-save-bar .btn,
#user_tab_submit_tabs .submit-tabs-save-bar .btn,
#user_tab_dynamic_fields .account-dynamic-fields-add-bar .btn {
    pointer-events: auto !important;
    position: relative;
    z-index: 101;
    box-shadow: 0 3px 10px rgba(15, 23, 42, .16);
}

/* Preserve scroll clearance without creating a visible backing panel. */
#user_tab_submit_tabs #submitTabsEditor,
#user_tab_dynamic_fields #userGlobalDynamicFieldsList,
#dynamicTabsEditor .dynamic-tabs-editor-list {
    padding-bottom: 76px !important;
}

@media (max-width: 640px) {
    #user_tab_submit_tabs .submit-tabs-save-bar,
    #user_tab_dynamic_fields .account-dynamic-fields-add-bar,
    #dynamicTabsEditor .dynamic-tabs-save-bar {
        justify-content: flex-end !important;
        padding: 0 !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    #user_tab_submit_tabs .submit-tabs-save-bar .btn,
    #user_tab_dynamic_fields .account-dynamic-fields-add-bar .btn,
    #dynamicTabsEditor .dynamic-tabs-save-bar .btn {
        width: auto !important;
        max-width: 100%;
    }
}


/* ===== Dynamic tab editor interaction updates ===== */
#dynamicTabsEditor .tab-editor-heading {
    cursor: pointer;
}
#dynamicTabsEditor .tab-editor-heading:focus-visible {
    outline: 2px solid #087f75;
    outline-offset: -2px;
}
#dynamicTabsEditor .tab-editor-item:not(.is-expanded) .tab-delete-button {
    display: none !important;
}
#dynamicTabsEditor .tab-editor-item.is-expanded .tab-delete-button {
    display: inline-flex !important;
}
#dynamicTabsEditor .display-tab-setting select.display-tab-input {
    width: 100%;
    max-width: 220px;
    min-height: 40px;
    padding: 9px 12px;
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background: #fff;
    color: #172033;
    cursor: pointer;
}
#dynamicTabsEditor .tab-editor-heading .tab-editor-actions {
    cursor: default;
}


/* ===== STICKY NAV VISUAL SPACING FIX (preserve existing scroll hand-off) =====
   Keep the default account tabs, dynamic main tabs, and nested tabs flush
   vertically. This changes only default layout spacing; sticky positioning,
   z-index priority, sentinels, and scroll listeners remain untouched.
*/
.user-config-tabs {
    margin-bottom: 0 !important;
}
.user-config-content {
    padding-top: 0 !important;
}
#user_tab_add_entry #newProjectSubTabs {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
/* Remove the parent container's top inset above the nested sticky row. */
#user_tab_add_entry .nested-project-tabs {
    padding-top: 0 !important;
}
/* Do not add a gap above the nested sticky row or between its own tabs. */
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
/* Keep tab rows edge-to-edge without changing their horizontal button spacing. */
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    align-self: stretch;
}
/* Keep the nested sub-tab row flush with the very top of its parent element.
   The sticky row previously had 10px (9px on mobile) of top padding, which
   made its buttons look separated from the main dynamic tab above it.
   This is a visual-only change: sticky positioning and scroll hand-off stay intact. */
#user_tab_add_entry .nested-project-tabs {
    padding-top: 0 !important;
}
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

/* ===== END STICKY NAV VISUAL SPACING FIX ===== */

/* ===== FINAL FIX: SUB-TAB STICKY ROW TOUCHES MAIN DYNAMIC TAB =====
   The active dynamic-tab content had top padding before its nested tabs.
   Remove only that inset when the content contains nested-project-tabs, so
   the child sticky row begins flush against the bottom of #newProjectSubTabs.
   Sticky top offsets, z-index priority, sentinels, and scroll hand-off stay intact.
*/
#user_tab_add_entry .dynamic-sub-tab-content:has(.nested-project-tabs) {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

#user_tab_add_entry .dynamic-sub-tab-content .nested-project-tabs {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

#user_tab_add_entry .dynamic-sub-tab-content .nested-project-tabs > .dynamic-sub-tabs {
    margin-top: 0 !important;
    padding-top: 0 !important;
    top: 0 !important;
}

@supports not selector(.dynamic-sub-tab-content:has(.nested-project-tabs)) {
    /* Fallback for older browsers: remove the top inset from the content row. */
    #user_tab_add_entry .dynamic-sub-tab-content {
        padding-top: 0 !important;
    }
}
/* ===== END FINAL SUB-TAB FLUSH FIX ===== */

/* ===== SUB-TAB STICKY HEIGHT, CENTERING, AND LEFT-AXIS ALIGNMENT =====
   Match the nested sticky row to the main dynamic-tab row's measured height,
   plus 2px. The buttons stay vertically centered, and their left edge aligns
   with the first main dynamic-tab button. Sticky hand-off logic is unchanged.
*/
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    display: flex !important;
    align-items: center !important;
    box-sizing: border-box !important;
    min-height: 0 !important;
    height: var(--nested-sticky-nav-height, auto) !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 42px !important;
    padding-right: 32px !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    background: #f8fcfb !important;
    opacity: 1 !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > .nested-child-btn {
    align-self: center !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    flex-shrink: 0;
}

@media (max-width: 760px) {
    #user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
        padding-left: 34px !important;
        padding-right: 26px !important;
    }
}
/* ===== END SUB-TAB STICKY HEIGHT, CENTERING, AND LEFT-AXIS ALIGNMENT ===== */




/* ===== REQUESTED STICKY TAB CLEAN WHITE DESIGN (CSS ONLY) =====
   Keep all existing sticky positioning and scroll hand-off behaviour.
   Remove outlines, border colors, rounded corners, shadows, and tinted
   backgrounds from the default, main dynamic, and nested sub-tab areas.
*/
.user-config-tabs,
.user-config-tabs.default-nav-released {
    border-bottom: 0 !important;
    background: #fff !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}

/* Main dynamic sticky tab row and its buttons */
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry #newProjectSubTabs .dynamic-sub-tab-btn,
#user_tab_add_entry #newProjectSubTabs .dynamic-sub-tab-btn:hover,
#user_tab_add_entry #newProjectSubTabs .dynamic-sub-tab-btn.active {
    border: 0 !important;
    border-color: transparent !important;
    border-radius: 0 !important;
    outline-color: transparent !important;
    box-shadow: none !important;
    background: #fff !important;
}

/* Nested sticky sub-tab row and all of its buttons */
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs .nested-child-btn,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs .nested-child-btn:hover,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs .nested-child-btn.active {
    border: 0 !important;
    border-color: transparent !important;
    border-radius: 0 !important;
    outline-color: transparent !important;
    box-shadow: none !important;
    background: #fff !important;
}

/* Make all tab content and nested containers plain white, without outlines */
#user_tab_add_entry .dynamic-sub-tab-content,
#user_tab_add_entry .nested-project-tabs,
#user_tab_add_entry .nested-child-content {
    border: 0 !important;
    border-color: transparent !important;
    border-radius: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
    background: #fff !important;
}

/* Remove any remaining bottom divider from the default and dynamic tab rows */
.user-config-tabs,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    border-top: 0 !important;
    border-right: 0 !important;
    border-bottom: 0 !important;
    border-left: 0 !important;
    background-color: #fff !important;
    -webkit-backdrop-filter: none !important;
    backdrop-filter: none !important;
}


/* ===== FINAL TAB ALIGNMENT + ACTIVE UNDERLINE =====
   Keep the existing sticky positioning and scroll hand-off behaviour.
   Remove row-level horizontal inset so the first dynamic/sub-tab button
   starts on the same left axis as the default New Project button.
*/
#user_tab_add_entry #newProjectSubTabs {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    gap: 0 !important;
    border: 0 !important;
    background: #fff !important;
}

#user_tab_add_entry #newProjectSubTabs > .dynamic-sub-tab-btn {
    flex: 0 0 auto;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
    border: 0 !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: #fff !important;
    box-sizing: border-box;
}

#user_tab_add_entry #newProjectSubTabs > .dynamic-sub-tab-btn.active {
    border-bottom: 2px solid #00695c !important;
    color: #00695c !important;
    font-weight: 700 !important;
    background: #fff !important;
}

/* Nested sub-tab row: remove row and first-button left/right insets. */
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    gap: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: #fff !important;
    box-shadow: none !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > .nested-child-btn {
    flex: 0 0 auto;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
    border: 0 !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: #fff !important;
    box-sizing: border-box;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > .nested-child-btn.active {
    border-bottom: 2px solid #00695c !important;
    color: #00695c !important;
    font-weight: 700 !important;
    background: #fff !important;
}

/* Prevent inherited first-child offsets from shifting either tab row. */
#user_tab_add_entry #newProjectSubTabs > :first-child,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > :first-child {
    margin-left: 0 !important;
}


/* ===== FINAL FIX: NESTED SUB-TAB ROW MUST MATCH MAIN DYNAMIC ROW WIDTH =====
   The nested row and its first button must share the exact same left axis and
   full available width as #newProjectSubTabs. Remove horizontal padding,
   margins, negative offsets, and parent insets that could make the row appear
   narrower or start 10% inward. Sticky positioning and scroll hand-off remain
   unchanged.
*/
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry .dynamic-sub-tab-content,
#user_tab_add_entry .dynamic-sub-tab-content:has(.nested-project-tabs),
#user_tab_add_entry .dynamic-sub-tab-content .nested-project-tabs,
#user_tab_add_entry .nested-project-tabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    box-sizing: border-box !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

#user_tab_add_entry .dynamic-sub-tab-content:has(.nested-project-tabs),
#user_tab_add_entry .dynamic-sub-tab-content .nested-project-tabs,
#user_tab_add_entry .nested-project-tabs {
    padding-left: 0 !important;
    padding-right: 0 !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    align-self: stretch !important;
    justify-content: flex-start !important;
    box-sizing: border-box !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > .nested-child-btn,
#user_tab_add_entry #newProjectSubTabs > .dynamic-sub-tab-btn {
    margin-left: 0 !important;
    flex-shrink: 0 !important;
}

@media (max-width: 760px) {
    #user_tab_add_entry .dynamic-sub-tab-content:has(.nested-project-tabs),
    #user_tab_add_entry .dynamic-sub-tab-content .nested-project-tabs,
    #user_tab_add_entry .nested-project-tabs,
    #user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
}
/* ===== END FINAL FULL-WIDTH SUB-TAB ALIGNMENT FIX ===== */


/* ===== EXACT GLOBAL-HEADER-TO-STICKY-NAV CONTACT FIX =====
   .scroll-body begins immediately below .main-header. A sticky top of 0
   therefore pins each navigation row directly to the header's bottom edge.
   No header-height offset, bottom offset, or extra sticky gap is used.
*/
.user-config-tabs,
.user-config-tabs.default-nav-released,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry.child-nav-priority #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    top: 0 !important;
    scroll-margin-top: 0 !important;
}

/* ELIMINATE THE HEADER-TO-STICKY GAP AT ITS SOURCE.
   The scroll viewport starts directly under .main-header. Remove all top
   padding from that viewport on desktop and mobile so sticky rows can meet
   the header edge with no 15px/10px inset. */
.scroll-body {
    padding-top: 0 !important;
    scroll-padding-top: 0 !important;
}

/* Keep the header-gap fix, restore the sticky rows' full available width,
   and remove bottom padding from the sticky row containers themselves. */
.user-config-tabs,
.user-config-tabs.default-nav-released,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry.child-nav-priority #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    top: 0 !important;
    margin-top: 0 !important;
    scroll-margin-top: 0 !important;
    translate: 0 0 !important;
    padding-bottom: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

/* Preserve the original horizontal layout of the page; only the top inset
   is removed from the scroll viewport. */
.scroll-body {
    padding-top: 0 !important;
    scroll-padding-top: 0 !important;
}

/* The sentinel checks switch priority only when the sentinel reaches the
   exact scroll viewport top, with no early 1px allowance. */

/* ===== FINAL CORRECTION: NO STICKY-ROW PADDING + MATCH CONTENT-AREA WIDTH =====
   Keep the top-contact fix exactly as it is.
   The content-area has 20px of internal horizontal padding, so each navigation
   row expands by that exact amount on both sides to match the content-area's
   outer width. Row containers themselves have zero left/right/bottom padding.
   Button padding is deliberately preserved so button labels remain readable.
*/
.content-area > .user-config-tabs,
.content-area .user-config-tabs,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry.child-nav-priority #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    box-sizing: border-box !important;
    width: calc(100% + 40px) !important;
    max-width: none !important;
    min-width: 0 !important;
    margin-left: -20px !important;
    margin-right: -20px !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 0 !important;
    padding-block-end: 0 !important;
    scroll-margin-top: 0 !important;
    top: 0 !important;
    translate: 0 0 !important;
}

/* Explicitly remove any bottom padding from the nested row, including mobile
   overrides and earlier height/alignment rules. */
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-block: 0 !important;
}

/* The main row has no bottom padding either; only the buttons retain their
   own horizontal padding. */
#user_tab_add_entry #newProjectSubTabs {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-block: 0 !important;
}

/* Preserve the exact header contact: no top inset in the scroll viewport. */
.scroll-body {
    padding-top: 0 !important;
    scroll-padding-top: 0 !important;
}
/* ===== END EXACT GLOBAL-HEADER-TO-STICKY-NAV CONTACT FIX ===== */


/* ===== EXACT STICKY NAV HEIGHT HIERARCHY =====
   default account tabs are 1px shorter than the main dynamic row;
   the nested row is 1px taller than the main dynamic row.
   JS measures the main row and applies the exact pixel heights.
*/
.user-config-tabs,
.user-config-tabs.default-nav-released,
#user_tab_add_entry #newProjectSubTabs,
#user_tab_add_entry.child-nav-priority #newProjectSubTabs,
#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    box-sizing: border-box !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    align-items: center !important;
}

.user-config-tabs,
.user-config-tabs.default-nav-released {
    min-height: 0 !important;
}

.user-config-tabs > .user-config-tab-btn {
    min-height: 0 !important;
    align-self: center !important;
}

#user_tab_add_entry #newProjectSubTabs {
    min-height: 0 !important;
}

#user_tab_add_entry #newProjectSubTabs > .dynamic-sub-tab-btn {
    min-height: 0 !important;
    align-self: center !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs {
    min-height: 0 !important;
}

#user_tab_add_entry .nested-project-tabs > .dynamic-sub-tabs > .nested-child-btn {
    min-height: 0 !important;
    align-self: center !important;
}
/* ===== END EXACT STICKY NAV HEIGHT HIERARCHY ===== */


/* ===== Requested navigation and account-list updates ===== */
.two-col.dashboard-layout { display:block !important; grid-template-columns:minmax(0,1fr) !important; gap:0 !important; margin-top:0 !important; }
.two-col.dashboard-layout > .content-area { width:100% !important; max-width:100% !important; min-width:0 !important; }
/* Keep tab rows horizontally scrollable when their buttons exceed the available width, but hide every scrollbar. */
.dashboard-tabs, .user-config-tabs, .dynamic-sub-tabs, #newProjectSubTabs,
#dynamicTabsEditor .dynamic-sub-tabs, .nested-project-tabs > .dynamic-sub-tabs,
.nested-project-tabs .dynamic-sub-tabs {
    display:flex !important; flex-wrap:nowrap !important; overflow-x:auto !important; overflow-y:hidden !important;
    max-width:100% !important; min-width:0 !important; white-space:nowrap !important;
    scrollbar-width:none !important; -ms-overflow-style:none !important; -webkit-overflow-scrolling:touch;
}
.dashboard-tabs::-webkit-scrollbar, .user-config-tabs::-webkit-scrollbar, .dynamic-sub-tabs::-webkit-scrollbar,
#newProjectSubTabs::-webkit-scrollbar, #dynamicTabsEditor .dynamic-sub-tabs::-webkit-scrollbar,
.nested-project-tabs > .dynamic-sub-tabs::-webkit-scrollbar, .nested-project-tabs .dynamic-sub-tabs::-webkit-scrollbar,
*::-webkit-scrollbar { display:none !important; width:0 !important; height:0 !important; }
* { scrollbar-width:none !important; }
.dashboard-tab-btn, .user-config-tab-btn, .dynamic-sub-tab-btn, .nested-child-btn { flex:0 0 auto !important; }
.accounts-list { display:flex; flex-direction:column; gap:8px; width:100%; }
.account-list-row { margin:0; width:100%; }
.account-list-select { display:flex; align-items:center; justify-content:space-between; gap:14px; width:100%; min-width:0; padding:14px 16px; text-align:left; background:#fff; border:1px solid #e5e7eb; border-radius:10px; cursor:pointer; }
.account-list-select:hover { background:#f8fafc; border-color:#00897b; }
.account-list-name { font-weight:650; color:#1f2937; overflow-wrap:anywhere; }
.account-list-email { color:#6b7280; font-size:13px; overflow-wrap:anywhere; text-align:right; }
.accounts-empty { padding:28px 12px; color:#6b7280; text-align:center; }
.menu-drawer-overlay { position:fixed; inset:0; z-index:5000; background:rgba(15,23,42,.42); opacity:0; visibility:hidden; pointer-events:none; transition:opacity .22s ease, visibility .22s ease; }
.menu-drawer-overlay.active { opacity:1; visibility:visible; pointer-events:auto; }
.menu-drawer { position:absolute; top:0; left:0; bottom:0; width:min(340px,86vw); background:#fff; box-shadow:8px 0 30px rgba(0,0,0,.18); transform:translateX(-105%); transition:transform .25s ease; padding:20px 16px; display:flex; flex-direction:column; gap:10px; }
.menu-drawer-overlay.active .menu-drawer { transform:translateX(0); }
.menu-drawer-heading { display:flex; align-items:center; justify-content:space-between; font-size:20px; color:#0f172a; padding-bottom:12px; border-bottom:1px solid #e5e7eb; }
.menu-drawer-close { border:0; background:transparent; font-size:30px; line-height:1; cursor:pointer; color:#64748b; padding:0 5px; }
.menu-account-identity { padding:14px 12px; background:#f8fafc; border-radius:10px; overflow-wrap:anywhere; }
.menu-account-username { font-weight:700; color:#0f172a; margin-bottom:5px; }
.menu-account-email { color:#64748b; font-size:13px; }
.menu-drawer-item { width:100%; text-align:left; padding:13px 12px; border:0; border-radius:8px; background:#fff; color:#1f2937; font-size:15px; cursor:pointer; }
.menu-drawer-item:hover { background:#f1f5f9; color:#00695c; }
.change-password-form { padding:12px; margin:0 0 6px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; }
.change-password-form label { display:block; margin:8px 0 5px; color:#334155; font-size:13px; font-weight:600; }
.change-password-form input { display:block; width:100%; min-width:0; padding:10px; border:1px solid #cbd5e1; border-radius:7px; background:#fff; color:#0f172a; }
.menu-password-save { width:100%; margin-top:12px; padding:11px 12px; border:0; border-radius:8px; background:#00695c; color:#fff; font-weight:700; cursor:pointer; }
.menu-password-save:hover { background:#004d40; }
.password-form-message { margin-top:8px; color:#b91c1c; font-size:12px; }

@media (max-width:640px) { .account-list-select { align-items:flex-start; flex-direction:column; gap:5px; } .account-list-email { text-align:left; } }
</style>
</head>
<body>
    <div class="custom-body">
        <div class="main-header" style="display:flex;">
            <div><h1>SceneIQ <span></span></h1></div>
            <div>
                <button type="button" class="debug-btn" id="menuButton" onclick="openMenuDrawer()" aria-haspopup="dialog" aria-controls="menuDrawer">Menu</button>
            </div>
        </div>
        
        <div class="scroll-body">
            <div class="server-container">
                
                <?php if ($flashSuccess): ?>
                    <div class="notification success"> <?php echo htmlspecialchars($flashSuccess); ?></div>
                <?php endif; ?>
                <?php if ($flashError): ?>
                    <div class="notification error"> <?php echo htmlspecialchars($flashError); ?></div>
                <?php endif; ?>
                
                <div class="two-col dashboard-layout">
                    <div class="content-area">
                        <?php if ($selectedUserId > 0 && $selectedUser): ?>
                            <div class="user-config-tabs">
                                <button class="user-config-tab-btn  active" onclick="switchUserConfigTab('add_entry', this)"> New Project</button>
                                <button class="user-config-tab-btn" onclick="switchUserConfigTab('pending', this)"> Pending</button>
                                <button class="user-config-tab-btn" onclick="switchUserConfigTab('completed', this)"> Completed</button>
                                <button class="user-config-tab-btn" onclick="switchUserConfigTab('aborted', this)"> Aborted</button>
                            </div>
                            
                            <div id="user_tab_pending" class="user-config-content">
                                <div id="pendingEntriesList"></div>
                            </div>
                            
                            <div id="user_tab_completed" class="user-config-content">
                                <div id="completedEntriesList"></div>
                            </div>
                            
                            <div id="user_tab_aborted" class="user-config-content">
                                <div id="abortedEntriesList"></div>
                            </div>
                            <div id="user_tab_add_entry" class="user-config-content active">
                                <?php $globalDynamicFields = $userDynamicFields; ?>
                                <?php if (empty($globalDynamicFields)): ?>
                                    <p style="color:#6b7280;">No project fields have been configured yet. Please contact management.</p>
                                <?php else: ?>
                                    <!-- Dynamic Sub Tabs for New Project -->
                                    <div class="dynamic-sub-tabs" id="newProjectSubTabs">
                                        <?php 
                                        $firstTabIndex = !empty($userDynamicTabs) ? array_key_first($userDynamicTabs) : -1;
                                        foreach ($userDynamicTabs as $tabIndex => $tab): 
                                            if (array_key_exists('display_tab', $tab) && empty($tab['display_tab'])) continue;
                                            $isActive = ($tabIndex === $firstTabIndex) ? 'active' : '';
                                        ?>
                                            <button type="button" class="dynamic-sub-tab-btn <?php echo $isActive; ?>" data-tab="tab_<?php echo $tabIndex; ?>" data-submit-enabled="<?php echo (!array_key_exists('submit_tab', $tab) || !empty($tab['submit_tab'])) ? '1' : '0'; ?>" onclick="switchNewProjectSubTab('tab_<?php echo $tabIndex; ?>', this)"> <?php echo htmlspecialchars($tab['tab_name'] ?? 'Tab ' . ($tabIndex + 1)); ?></button>
                                        <?php endforeach; ?>
                                    </div>
                                    
                                    <!-- All Fields Content -->
                                    <div id="newProjectSubTab_all_fields" class="dynamic-sub-tab-content">
                                        <?php renderNewProjectForm($globalDynamicFields, $selectedUserId); ?>
                                    </div>
                                    
                                    <!-- Dynamic Tab Contents -->
                                    <?php 
                                    $firstTabIndex = !empty($userDynamicTabs) ? array_key_first($userDynamicTabs) : -1;
                                    foreach ($userDynamicTabs as $tabIndex => $tab): 
                                        if (array_key_exists('display_tab', $tab) && empty($tab['display_tab'])) continue;
                                        $isActive = ($tabIndex === $firstTabIndex) ? 'active' : '';
                                    ?>
                                        <div id="newProjectSubTab_tab_<?php echo $tabIndex; ?>" class="dynamic-sub-tab-content <?php echo $isActive; ?>">
                                            <?php
                                                $children = (isset($tab['sub_tabs_mode']) && $tab['sub_tabs_mode'] === 'add' && !empty($tab['sub_tabs']) && is_array($tab['sub_tabs'])) ? array_values(array_filter($tab['sub_tabs'], function($child) { return !array_key_exists('display_tab', $child) || !empty($child['display_tab']); })) : [];
                                                if (!empty($children)):
                                            ?>
                                                <?php if (!empty($tab['header']) || !empty($tab['description'])): ?>
                                                    <div style="margin-bottom:12px;padding:10px;background:#f0fdf4;border-radius:8px;border-left:4px solid #00695c;">
                                                        <?php if (!empty($tab['header'])): ?><h4 style="color:#00695c;"><?php echo htmlspecialchars($tab['header']); ?></h4><?php endif; ?>
                                                        <?php if (!empty($tab['description'])): ?><p style="color:#6b7280;font-size:14px;"><?php echo htmlspecialchars($tab['description']); ?></p><?php endif; ?>
                                                    </div>
                                                <?php endif; ?>
                                                <div class="nested-project-tabs" data-parent-tab="<?php echo $tabIndex; ?>">
                                                    <div class="dynamic-sub-tabs" style="margin-bottom:12px;">
                                                        <?php foreach ($children as $childIndex => $child): ?>
                                                            <button type="button" class="dynamic-sub-tab-btn nested-child-btn <?php echo $childIndex === 0 ? 'active' : ''; ?>" onclick="switchNewProjectNestedSubTab(this)"><?php echo htmlspecialchars($child['tab_name'] ?? ('Sub Tab ' . ($childIndex + 1))); ?></button>
                                                        <?php endforeach; ?>
                                                    </div>
                                                    <?php foreach ($children as $childIndex => $child):
                                                        $childFields = [];
                                                        foreach (($child['dynamic_fields_display'] ?? []) as $childFieldKey) {
                                                            if (isset($globalDynamicFields[$childFieldKey])) $childFields[$childFieldKey] = $globalDynamicFields[$childFieldKey];
                                                        }
                                                    ?>
                                                        <div class="nested-child-content <?php echo $childIndex === 0 ? 'active' : ''; ?>" style="display:<?php echo $childIndex === 0 ? 'block' : 'none'; ?>;">
                                                            <?php if (!empty($child['header']) || !empty($child['description'])): ?>
                                                                <div style="margin-bottom:12px;padding:10px;background:#f0fdf4;border-radius:8px;border-left:4px solid #00695c;">
                                                                    <?php if (!empty($child['header'])): ?><h4 style="color:#00695c;"><?php echo htmlspecialchars($child['header']); ?></h4><?php endif; ?>
                                                                    <?php if (!empty($child['description'])): ?><p style="color:#6b7280;font-size:14px;"><?php echo htmlspecialchars($child['description']); ?></p><?php endif; ?>
                                                                </div>
                                                            <?php endif; ?>
                                                            <?php if (!empty($childFields)) renderNewProjectForm($childFields, $selectedUserId); else echo '<p style="color:#6b7280;">No fields selected for this sub-tab.</p>'; ?>
                                                        </div>
                                                    <?php endforeach; ?>
                                                </div>
                                            <?php else:
                                                $displayFields = $tab['dynamic_fields_display'] ?? [];
                                                $filteredFields = [];
                                                foreach ($displayFields as $fieldKey) if (isset($globalDynamicFields[$fieldKey])) $filteredFields[$fieldKey] = $globalDynamicFields[$fieldKey];
                                            ?>
                                                <?php if (!empty($tab['header']) || !empty($tab['description'])): ?>
                                                    <div style="margin-bottom:15px;padding:10px;background:#f0fdf4;border-radius:8px;border-left:4px solid #00695c;">
                                                        <?php if (!empty($tab['header'])): ?><h4 style="color:#00695c;"><?php echo htmlspecialchars($tab['header']); ?></h4><?php endif; ?>
                                                        <?php if (!empty($tab['description'])): ?><p style="color:#6b7280;font-size:14px;"><?php echo htmlspecialchars($tab['description']); ?></p><?php endif; ?>
                                                    </div>
                                                <?php endif; ?>
                                                <?php if (!empty($filteredFields)) renderNewProjectForm($filteredFields, $selectedUserId); ?>
                                            <?php endif; ?>
                                        </div>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </div>

                            <div id="user_tab_pending" class="user-config-content">
                                <div id="pendingEntriesList"></div>
                            </div>

                            <div id="user_tab_completed" class="user-config-content">
                                <div id="completedEntriesList"></div>
                            </div>

                            <div id="user_tab_aborted" class="user-config-content">
                                <div id="abortedEntriesList"></div>
                            </div>
                            
                        <?php else: ?>
                            <div class="dashboard-tabs" role="tablist" aria-label="Account dashboard">
                                <button type="button" class="dashboard-tab-btn <?php echo ($dashboardView === 'initialize') ? 'active' : ''; ?>" onclick="switchDashboardTab('initialize', this)">Initialize Account</button>
                                <button type="button" class="dashboard-tab-btn <?php echo ($dashboardView === 'accounts') ? 'active' : ''; ?>" onclick="switchDashboardTab('accounts', this)">All Accounts</button>
                                <button type="button" class="dashboard-tab-btn <?php echo ($dashboardView === 'all_config') ? 'active' : ''; ?>" onclick="switchDashboardTab('all_config', this)">All Account Config</button>
                            </div>
                            
                            <div id="dash_tab_initialize" class="dashboard-content <?php echo ($dashboardView === 'initialize') ? 'active' : ''; ?>">
                                <div class="create-user-form">
                                    <h3> Create New Account</h3>
                                    <form method="POST" id="createUserForm">
                                        <div class="form-row">
                                            <input type="email" name="email" placeholder="Email" required>
                                            <input type="text" name="username" placeholder="Username" required>
                                            <input type="password" name="password" placeholder="Password (min 6 chars)" required minlength="6">
                                            <button type="submit" name="create_user" class="btn-create">Create Account</button>
                                            <button class="btn-create" onclick="window.location.href='users.php'">Login as a Account</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                            
                            <div id="dash_tab_accounts" class="dashboard-content <?php echo ($dashboardView === 'accounts') ? 'active' : ''; ?>">
                                <div class="accounts-list" id="allAccountsList">
                                    <?php if (empty($users)): ?>
                                        <p class="accounts-empty">No accounts found. Create an account first.</p>
                                    <?php else: ?>
                                        <?php foreach ($users as $user): ?>
                                            <form method="POST" class="account-list-row">
                                                <input type="hidden" name="select_user" value="1">
                                                <input type="hidden" name="user_id" value="<?php echo (int)$user['id']; ?>">
                                                <button type="submit" class="account-list-select">
                                                    <span class="account-list-name"><?php echo htmlspecialchars($user['username']); ?></span>
                                                    <span class="account-list-email"><?php echo htmlspecialchars($user['email']); ?></span>
                                                </button>
                                            </form>
                                        <?php endforeach; ?>
                                    <?php endif; ?>
                                </div>
                            </div>
                            
                            <div id="dash_tab_all_config" class="dashboard-content <?php echo ($dashboardView === 'all_config') ? 'active' : ''; ?>">
                                <h3 style="margin-bottom:15px; color:#1a1a2e;">All Account Configuration</h3>
                                
                                <?php if (empty($users)): ?>
                                    <p style="color:#6b7280; text-align:center; padding:40px;">No users found. Create a user first.</p>
                                <?php else: ?>
                                <?php endif; ?>
                            </div>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- ===== LEFT MENU DRAWER ===== -->
    <div class="menu-drawer-overlay" id="menuDrawerOverlay" onclick="closeMenuDrawer(event)" aria-hidden="true">
        <aside class="menu-drawer" id="menuDrawer" role="dialog" aria-modal="true" aria-label="Main menu">
            <div class="menu-drawer-heading">
                <strong>Menu</strong>
                <button type="button" class="menu-drawer-close" onclick="closeMenuDrawer()" aria-label="Close menu">×</button>
            </div>
            <div class="menu-account-identity">
                <div class="menu-account-username">Username: <?php echo htmlspecialchars($selectedUser['username'] ?? '—'); ?></div>
                <div class="menu-account-email">Email: <?php echo htmlspecialchars($selectedUser['email'] ?? '—'); ?></div>
            </div>
            <?php if ($selectedUser): ?>
            <button type="button" class="menu-drawer-item" id="changePasswordToggle" onclick="toggleChangePasswordForm()" aria-expanded="false">Change Password</button>
            <form method="POST" id="changePasswordForm" class="change-password-form" style="display:none;">
                <input type="hidden" name="change_account_password" value="1">
                <input type="hidden" name="password_user_id" value="<?php echo (int)$selectedUser['id']; ?>">
                <input type="hidden" name="password_csrf_token" value="<?php echo htmlspecialchars($_SESSION['password_csrf_token'], ENT_QUOTES, 'UTF-8'); ?>">
                <label for="newPassword">New password</label>
                <input type="password" id="newPassword" name="new_password" minlength="8" autocomplete="new-password" required>
                <label for="confirmPassword">Confirm password</label>
                <input type="password" id="confirmPassword" name="confirm_password" minlength="8" autocomplete="new-password" required>
                <button type="submit" class="menu-password-save">Save Password</button>
                <p id="passwordFormMessage" class="password-form-message" aria-live="polite"></p>
            </form>
            <?php endif; ?>
            <form method="POST" style="margin:0;">
                <button type="submit" name="member_logout" value="1" class="menu-drawer-item" style="color:#b91c1c;font-weight:700;">Log Out</button>
            </form>
        </aside>
    </div>

    <!-- ===== CUSTOM DIALOG ===== -->
    <div class="custom-dialog-overlay" id="customDialog">
        <div class="custom-dialog-box">
            <div class="dialog-title" id="dialogTitle">Notification</div>
            <div class="dialog-message" id="dialogMessage">Message here</div>
            <div id="dialogContent" style="margin-bottom:15px;"></div>
            <div class="dialog-buttons" id="dialogButtons">
                <button class="btn btn-primary" onclick="closeDialog()">OK</button>
            </div>
        </div>
    </div>
    
    <!-- ===== USER SEARCH DIALOG ===== -->
    <div class="custom-dialog-overlay user-search-modal" id="userSearchDialog">
        <div class="custom-dialog-box">
            <div class="dialog-header">
                <h2> Select Account</h2>
                <input type="text" class="search-input" id="userSearchInput" placeholder="Type to Search Account..." onkeyup="filterUserSearch()">
            </div>
            <div class="dialog-body" id="userSearchResults">
                <?php foreach ($users as $user): ?>
                    <div class="user-search-item" data-user-id="<?php echo $user['id']; ?>" data-user-name="<?php echo strtolower(htmlspecialchars($user['username'])); ?>" data-user-email="<?php echo strtolower(htmlspecialchars($user['email'])); ?>" onclick="selectUserFromSearch(<?php echo $user['id']; ?>)">
                        <div class="user-name"><?php echo htmlspecialchars($user['username']); ?></div>
                        <div class="user-email"><?php echo htmlspecialchars($user['email']); ?></div>
                    </div>
                <?php endforeach; ?>
            </div>
            <div class="dialog-footer">
                <button class="btn btn-secondary" onclick="closeUserSearchDialog()">Close</button>
            </div>
        </div>
    </div>

<?php
    function renderNewProjectForm($dynamicFields, $selectedUserId) {
        if (empty($dynamicFields)) {
            echo '<p style="color:#6b7280;">No fields available for this view.</p>';
            return;
        }
        ?>
        <form method="POST" id="addEntryForm">
            <input type="hidden" name="add_entry" value="true">
            <input type="hidden" name="user_id" value="<?php echo $selectedUserId; ?>">
            <input type="hidden" name="entry_data" id="entryDataInput">
            
            <?php foreach ($dynamicFields as $key => $field): ?>
                <?php if ($field['field_type'] === 'objects'): ?>
                    <div class="form-group" style="border:2px solid #00695c; border-radius:10px; padding:15px; margin-bottom:15px;">
                        <h4 style="color:#00695c; margin-bottom:10px;"> <?php echo htmlspecialchars($field['field-title'] ?? $key); ?></h4>
                        <div id="object_<?php echo $key; ?>_container">
                            <?php 
                                $subFields = $field['fieldkeyvalue'] ?? [];
                                foreach ($subFields as $subKey => $subField):
                                    $elementType = $subField['element_type'] ?? 'input';
                                    $title = $subField['field-title'] ?? $subKey;
                                    $defaultValue = $subField['default_value'] ?? '';
                                    $buttonUrl = $subField['button_url'] ?? '';
                            ?>
                                <div class="sub-field-group">
                                    <label><?php echo htmlspecialchars($title); ?></label>
                                    <?php if ($elementType === 'date-time-input'): ?>
                                        <div class="datetime-group">
                                            <input type="date" id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>_date" class="date-input" value="<?php echo htmlspecialchars($defaultValue); ?>">
                                            <div class="time-group">
                                                <input type="number" id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>_hour_12" placeholder="HH" min="1" max="12" style="width:60px;">
                                                <span>:</span>
                                                <input type="number" id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>_minute_12" placeholder="MM" min="0" max="59" style="width:60px;">
                                                <select id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>_ampm" style="width:70px;">
                                                    <option value="AM">AM</option>
                                                    <option value="PM">PM</option>
                                                </select>
                                                <span style="color:#6b7280; font-size:12px; margin-left:5px;">(12h format)</span>
                                            </div>
                                        </div>
                                    <?php elseif ($elementType === 'textarea'): ?>
                                        <?php if (($subField['separate_paragraphs'] ?? 'no') === 'yes' && trim($defaultValue) !== ''): ?>
                                            <div class="separated-default-paragraphs" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;">
                                                <?php foreach (preg_split('/\R+/', trim($defaultValue)) as $paragraph): $paragraph = trim($paragraph); if ($paragraph === '') continue; ?>
                                                    <div style="padding:10px;border:1px solid #d1d5db;border-radius:8px;background:#f9fafb;">
                                                        <div style="white-space:pre-wrap;margin-bottom:7px;"><?php echo htmlspecialchars($paragraph); ?></div>
                                                        <button type="button" class="btn btn-secondary btn-sm" data-copy-text="<?php echo htmlspecialchars($paragraph, ENT_QUOTES); ?>" onclick="copyToClipboard(this.getAttribute('data-copy-text'), this)">📋 Copy</button>
                                                    </div>
                                                <?php endforeach; ?>
                                            </div>
                                            <textarea id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>" rows="3" style="display:none;" class="field-with-default new-project-field" data-field-key="<?php echo $key; ?>" data-sub-key="<?php echo $subKey; ?>"><?php echo htmlspecialchars($defaultValue); ?></textarea>
                                        <?php else: ?>
                                            <textarea id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>" rows="3" placeholder="Enter <?php echo htmlspecialchars($title); ?>..." class="field-with-default new-project-field" data-field-key="<?php echo $key; ?>" data-sub-key="<?php echo $subKey; ?>"><?php echo htmlspecialchars($defaultValue); ?></textarea>
                                        <?php endif; ?>
                                    <?php elseif ($elementType === 'select'): ?>
                                        <select id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>" class="new-project-field" data-field-key="<?php echo $key; ?>" data-sub-key="<?php echo $subKey; ?>">
                                            <option value="">Select...</option>
                                            <?php foreach (($subField['default_values'] ?? []) as $val): ?>
                                                <option value="<?php echo htmlspecialchars($val); ?>" <?php echo ($val === $defaultValue) ? 'selected' : ''; ?>><?php echo htmlspecialchars($val); ?></option>
                                            <?php endforeach; ?>
                                        </select>
                                    <?php elseif ($elementType === 'button'): ?>
                                        <div>
                                            <button type="button" class="btn btn-primary" onclick="openUrl('<?php echo htmlspecialchars(trim($buttonUrl), ENT_QUOTES); ?>')" style="padding:8px 20px;">
                                                <?php echo htmlspecialchars($title); ?>
                                            </button>
                                            <input type="hidden" id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>" value="<?php echo htmlspecialchars($buttonUrl); ?>" class="new-project-field" data-field-key="<?php echo $key; ?>" data-sub-key="<?php echo $subKey; ?>">
                                        </div>
                                    <?php else: ?>
                                        <input type="text" id="entry_<?php echo $key; ?>_<?php echo $subKey; ?>" placeholder="Enter <?php echo htmlspecialchars($title); ?>..." value="<?php echo htmlspecialchars($defaultValue); ?>" class="new-project-field" data-field-key="<?php echo $key; ?>" data-sub-key="<?php echo $subKey; ?>">
                                    <?php endif; ?>
                                </div>
                            <?php endforeach; ?>
                        </div>
                        <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                            <button type="button" class="btn btn-secondary btn-sm" onclick="copyObjectFromDOM(this)">📋 Copy data</button>
                        </div>
                        <input type="hidden" id="object_<?php echo $key; ?>_data" value="">
                    </div>
                <?php else: ?>
                    <div class="form-group" id="field_group_<?php echo $key; ?>">
                        <label><?php echo htmlspecialchars($field['field-title'] ?? $key); ?></label>
                        <?php 
                            $elementType = $field['element_type'] ?? 'input';
                            $defaultValue = $field['default_value'] ?? '';
                            $defaultValues = $field['default_values'] ?? [];
                            $buttonUrl = $field['button_url'] ?? '';
                        ?>
                        <?php if ($elementType === 'copy_button_for_each_of'): ?>
                            <div id="field_<?php echo htmlspecialchars($key); ?>_container" style="display:flex;flex-direction:column;gap:12px;margin:10px 0;">
                                <?php $copySentences = $field['copy_button_for_each_of'] ?? []; if (is_array($copySentences)): foreach ($copySentences as $sentence): $sentence = trim((string)$sentence); if ($sentence === '') continue; ?>
                                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:12px;border:1px solid #d1d5db;border-radius:8px;background:#f9fafb;margin-bottom:4px;">
                                        <div style="white-space:pre-wrap;overflow-wrap:anywhere;flex:1;min-width:0;"><?php echo htmlspecialchars($sentence); ?></div>
                                        <button type="button" class="btn btn-secondary btn-sm individual-sentence-copy-button" data-copy-text="<?php echo htmlspecialchars($sentence, ENT_QUOTES); ?>" onclick="copyToClipboard(this.getAttribute('data-copy-text'), this)">📋 Copy</button>
                                    </div>
                                <?php endforeach; endif; ?>
                                <input type="hidden" id="entry_<?php echo htmlspecialchars($key); ?>" value="" class="new-project-field" data-field-key="<?php echo htmlspecialchars($key); ?>">
                            </div>
                        <?php elseif ($elementType === 'date-time-input'): ?>
                            <div class="datetime-group" id="field_<?php echo $key; ?>_container">
                                <input type="date" id="entry_<?php echo $key; ?>_date" class="date-input new-project-field" data-field-key="<?php echo $key; ?>" value="<?php echo htmlspecialchars($defaultValue); ?>">
                                <div class="time-group">
                                    <input type="number" id="entry_<?php echo $key; ?>_hour_12" placeholder="HH" min="1" max="12" style="width:60px;">
                                    <span>:</span>
                                    <input type="number" id="entry_<?php echo $key; ?>_minute_12" placeholder="MM" min="0" max="59" style="width:60px;">
                                    <select id="entry_<?php echo $key; ?>_ampm" style="width:70px;">
                                        <option value="AM">AM</option>
                                        <option value="PM">PM</option>
                                    </select>
                                    <span style="color:#6b7280; font-size:12px; margin-left:5px;">(12h format)</span>
                                </div>
                                <div style="margin-top:5px; display:flex; gap:8px; flex-wrap:wrap;">
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualFromDOM(this)">📋 Copy Data</button>
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualDefaultValue(this)" style="display: none">📋 Copy Default Value</button>
                                </div>
                            </div>
                        <?php elseif ($elementType === 'textarea'): ?>
                            <div id="field_<?php echo $key; ?>_container">
                                <?php if (($field['separate_paragraphs'] ?? 'no') === 'yes' && trim($defaultValue) !== ''): ?>
                                    <div class="separated-default-paragraphs" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;">
                                        <?php foreach (preg_split('/\R+/', trim($defaultValue)) as $paragraph): $paragraph = trim($paragraph); if ($paragraph === '') continue; ?>
                                            <div style="padding:10px;border:1px solid #d1d5db;border-radius:8px;background:#f9fafb;">
                                                <div style="white-space:pre-wrap;margin-bottom:7px;"><?php echo htmlspecialchars($paragraph); ?></div>
                                                <button type="button" class="btn btn-secondary btn-sm" data-copy-text="<?php echo htmlspecialchars($paragraph, ENT_QUOTES); ?>" onclick="copyToClipboard(this.getAttribute('data-copy-text'), this)">📋 Copy</button>
                                            </div>
                                        <?php endforeach; ?>
                                    </div>
                                    <textarea id="entry_<?php echo $key; ?>" rows="3" style="display:none;" class="field-with-default new-project-field" data-field-key="<?php echo $key; ?>"><?php echo htmlspecialchars($defaultValue); ?></textarea>
                                <?php else: ?>
                                    <textarea id="entry_<?php echo $key; ?>" rows="3" placeholder="Enter <?php echo htmlspecialchars($field['field-title'] ?? $key); ?>..." class="field-with-default new-project-field" data-field-key="<?php echo $key; ?>"><?php echo htmlspecialchars($defaultValue); ?></textarea>
                                    <div style="margin-top:5px;display:flex;gap:8px;flex-wrap:wrap;">
                                        <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualFromDOM(this)">📋 Copy Data</button>
                                        <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualDefaultValue(this)" style="display:none">📋 Copy Default Value</button>
                                    </div>
                                <?php endif; ?>
                            </div>
                        <?php elseif ($elementType === 'select'): ?>
                            <div id="field_<?php echo $key; ?>_container">
                                <select id="entry_<?php echo $key; ?>" class="new-project-field" data-field-key="<?php echo $key; ?>">
                                    <option value="">Select...</option>
                                    <?php foreach ($defaultValues as $val): ?>
                                        <option value="<?php echo htmlspecialchars($val); ?>" <?php echo ($val === $defaultValue) ? 'selected' : ''; ?>><?php echo htmlspecialchars($val); ?></option>
                                    <?php endforeach; ?>
                                </select>
                                <div style="margin-top:5px; display:flex; gap:8px; flex-wrap:wrap;">
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualFromDOM(this)">📋 Copy Data</button>
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualDefaultValue(this)" style="display: none">📋 Copy Default Value</button>
                                </div>
                            </div>
                        <?php elseif ($elementType === 'button'): ?>
                            <div id="field_<?php echo $key; ?>_container">
                                <button type="button" class="btn btn-primary" onclick="openUrl('<?php echo htmlspecialchars(trim($buttonUrl), ENT_QUOTES); ?>')" style="padding:8px 20px;">
                                    <?php echo htmlspecialchars($field['field-title'] ?? $key); ?>
                                </button>
                                <input type="hidden" id="entry_<?php echo $key; ?>" value="<?php echo htmlspecialchars($buttonUrl); ?>" class="new-project-field" data-field-key="<?php echo $key; ?>">
                                <div style="margin-top:5px; display:flex; gap:8px; flex-wrap:wrap;">
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualFromDOM(this)">📋 Copy Data</button>
                                </div>
                            </div>
                        <?php else: ?>
                            <div id="field_<?php echo $key; ?>_container">
                                <input type="text" id="entry_<?php echo $key; ?>" placeholder="Enter <?php echo htmlspecialchars($field['field-title'] ?? $key); ?>..." value="<?php echo htmlspecialchars($defaultValue); ?>" class="new-project-field" data-field-key="<?php echo $key; ?>">
                                <div style="margin-top:5px; display:flex; gap:8px; flex-wrap:wrap;">
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualFromDOM(this)">📋 Copy Data</button>
                                    <button type="button" class="btn btn-secondary btn-sm" onclick="copyIndividualDefaultValue(this)" style="display: none">📋 Copy Default Value</button>
                                </div>
                            </div>
                        <?php endif; ?>
                    </div>
                <?php endif; ?>
            <?php endforeach; ?>
            
            <div class="form-actions">
                <button type="button" id="saveEntryButton" class="btn btn-success" onclick="submitUserEntry()" style="display:none;"> Save Entry</button>
            </div>
        </form>
        <?php
    }
?>

<script>
    function openUrl(url) {
        if (!url) return;
        // If URL doesn't have a protocol, add https://
        if (!url.match(/^https?:\/\//i)) {
            url = 'https://' + url;
        }
        window.open(url, '_blank');
    }
    // ===== DATA =====
    var selectedUserId = <?php echo json_encode($selectedUserId); ?>;
    var globalDynamicFields = <?php echo json_encode($globalDynamicFields); ?>;
    var userSettings = <?php echo json_encode($userSettings); ?>;
    var userDynamicTabs = <?php echo json_encode($userDynamicTabs); ?>;
    var allUsersEntries = <?php echo json_encode($allUsersEntries); ?>;
    var _pendingSaveData = null;

    // ============================================================
    // ===== BACKGROUND SYNC FUNCTIONS - KEEPS DATA FRESH =====
    // ============================================================

    window._fieldValueCache = {};

    function syncFieldValues() {
        var activeContent = document.querySelector('#user_tab_add_entry .dynamic-sub-tab-content.active');
        if (!activeContent) return;
        
        var fields = activeContent.querySelectorAll('.new-project-field');
        fields.forEach(function(field) {
            var id = field.id;
            if (!id) return;
            var value = field.value || '';
            var cacheKey = id;
            if (id.startsWith('entry_')) {
                cacheKey = id.replace('entry_', '');
            }
            window._fieldValueCache[cacheKey] = value;
        });
        
        var objectContainers = activeContent.querySelectorAll('[id^="object_"]');
        objectContainers.forEach(function(container) {
            var containerId = container.id;
            if (!containerId) return;
            var objectKey = containerId.replace('object_', '').replace('_container', '');
            var subFields = container.querySelectorAll('.sub-field-group');
            var objectData = {};
            subFields.forEach(function(subField) {
                var inputs = subField.querySelectorAll('input, textarea, select');
                inputs.forEach(function(input) {
                    if (input.id && input.id.startsWith('entry_' + objectKey + '_')) {
                        var subKey = input.id.replace('entry_' + objectKey + '_', '');
                        if (subKey.includes('_date') || subKey.includes('_hour_12') || 
                            subKey.includes('_minute_12') || subKey.includes('_ampm')) {
                            return;
                        }
                        objectData[subKey] = input.value || '';
                    }
                });
            });
            window._fieldValueCache[objectKey] = objectData;
        });
    }

    var syncInterval = null;

    function startBackgroundSync() {
        if (syncInterval) clearInterval(syncInterval);
        syncInterval = setInterval(function() {
            syncFieldValues();
        }, 1000);
    }

    function stopBackgroundSync() {
        if (syncInterval) {
            clearInterval(syncInterval);
            syncInterval = null;
        }
    }

    // ============================================================
    // ===== COPY FUNCTIONS =====
    // ============================================================

    // Resolve the field from the button that was actually clicked.
    // This avoids selecting a different copy of a field when the same field
    // key is rendered in more than one tab or view.
    function resolveCopyContainer(buttonOrContainer, kind) {
        if (buttonOrContainer && buttonOrContainer.nodeType === 1) {
            if (kind === 'object') {
                // The object Copy Data button is rendered AFTER (as a sibling of)
                // the object container, not inside it. Search the surrounding
                // field group first, then fall back to the closest object container.
                var objectGroup = buttonOrContainer.closest('.form-group');
                if (objectGroup) {
                    var objectContainer = objectGroup.querySelector('[id^="object_"][id$="_container"]');
                    if (objectContainer) {
                        return objectContainer;
                    }
                }
                return buttonOrContainer.closest('[id^="object_"][id$="_container"]');
            }

            // Individual-field buttons are normally inside their field container.
            var fieldContainer = buttonOrContainer.closest('[id^="field_"][id$="_container"]');
            if (fieldContainer) {
                return fieldContainer;
            }

            // Fallback for fields whose Copy Data button is adjacent to the
            // value control rather than nested in the container.
            var fieldGroup = buttonOrContainer.closest('.form-group');
            if (fieldGroup) {
                return fieldGroup.querySelector('[id^="field_"][id$="_container"]') || fieldGroup;
            }
            return null;
        }

        // Backward compatibility for callers still passing an element ID.
        if (typeof buttonOrContainer === 'string') {
            return document.getElementById(buttonOrContainer);
        }
        return null;
    }

    function copyIndividualFromDOM(buttonOrContainer) {
        var container = resolveCopyContainer(buttonOrContainer, 'individual');
        if (!container) {
            showDialog('Error', 'Could not find the field connected to this Copy Data button.');
            return;
        }

        // Read the live form control inside the exact field whose button was clicked.
        // Never use defaults, cached values, or text rendered in another tab.
        var valueElement = container.querySelector('.new-project-field, .field-with-default, textarea, select, input');
        if (!valueElement) {
            showDialog('Error', 'Value element not found in the selected field.');
            return;
        }

        var textToCopy = valueElement.value;
        if (textToCopy === undefined || textToCopy === null) {
            textToCopy = '';
        }
        copyToClipboard(String(textToCopy), buttonOrContainer);
    }

    function copyObjectFromDOM(buttonOrContainer) {
        var container = resolveCopyContainer(buttonOrContainer, 'object');
        if (!container) {
            showDialog('Error', 'Could not find the object connected to this Copy Data button.');
            return;
        }

        var subFields = container.querySelectorAll('.sub-field-group');
        var rows = [];

        subFields.forEach(function(subField) {
            var values = [];
            var inputs = subField.querySelectorAll('input, textarea, select');

            inputs.forEach(function(input) {
                if (input.id && (
                    input.id.includes('_date') ||
                    input.id.includes('_hour_12') ||
                    input.id.includes('_minute_12') ||
                    input.id.includes('_ampm')
                )) {
                    return;
                }
                if (input.type === 'button' || input.type === 'submit' ||
                    input.type === 'reset' || input.type === 'hidden') {
                    return;
                }
                values.push(input.value === undefined || input.value === null
                    ? ''
                    : String(input.value));
            });

            rows.push(values.join(' '));
        });

        copyToClipboard(rows.join('\n'), buttonOrContainer);
    }

    function getElementDefaultValue(valueElement) {
        if (!valueElement) {
            return '';
        }

        var tagName = valueElement.tagName ? valueElement.tagName.toLowerCase() : '';

        if (tagName === 'select') {
            // defaultSelected reflects the option marked as selected in the
            // original markup, not the option currently selected by the user.
            var defaultOption = null;
            for (var i = 0; i < valueElement.options.length; i++) {
                if (valueElement.options[i].defaultSelected) {
                    defaultOption = valueElement.options[i];
                    break;
                }
            }
            return defaultOption ? defaultOption.value : '';
        }

        // For input and textarea, defaultValue is the original value from the
        // markup. It remains independent of edits to the live .value property.
        if (typeof valueElement.defaultValue === 'string') {
            return valueElement.defaultValue;
        }

        return '';
    }

    function copyIndividualDefaultValue(buttonOrContainer) {
        var container = resolveCopyContainer(buttonOrContainer, 'individual');
        if (!container) {
            showDialog('Error', 'Field not found');
            return;
        }

        var valueElement = container.querySelector('input, textarea, select');
        if (!valueElement) {
            showDialog('Error', 'Value element not found');
            return;
        }

        // Copy Default Values reads the element's original default separately
        // from Copy Data and never uses the current edited value or cache.
        copyToClipboard(getElementDefaultValue(valueElement));
    }

    function copyObjectDefaultValues(buttonOrContainer) {
        var container = resolveCopyContainer(buttonOrContainer, 'object');
        if (!container) {
            showDialog('Error', 'Object container not found');
            return;
        }

        var subFields = container.querySelectorAll('.sub-field-group');
        var rows = [];

        subFields.forEach(function(subField) {
            var values = [];
            var inputs = subField.querySelectorAll('input, textarea, select');

            inputs.forEach(function(input) {
                if (input.id && (
                    input.id.includes('_date') ||
                    input.id.includes('_hour_12') ||
                    input.id.includes('_minute_12') ||
                    input.id.includes('_ampm')
                )) {
                    return;
                }

                if (input.type === 'button' || input.type === 'submit' || input.type === 'reset') {
                    return;
                }

                values.push(getElementDefaultValue(input));
            });

            rows.push(values.join(' '));
        });

        // Empty default values are valid and are copied as empty text/rows.
        copyToClipboard(rows.join('\n'));
    }

    function copyToClipboard(text, triggerElement) {
        // Do not reject an empty string. Copy Data must be able to copy a
        // field after its current value has been erased.
        var textToCopy = typeof text === 'string'
            ? text
            : (text === undefined || text === null ? '' : String(text));

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                showDialog('Success', textToCopy === '' ? 'Copied an empty value to clipboard.' : 'Copied to clipboard!');
            }).catch(function() {
                fallbackCopy(textToCopy);
            });
        } else {
            fallbackCopy(textToCopy);
        }
    }

    function fallbackCopy(text) {
        var textarea = document.createElement('textarea');
        textarea.value = text === undefined || text === null ? '' : String(text);
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '-9999px';
        textarea.style.width = '1px';
        textarea.style.height = '1px';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        var copied = false;
        try {
            copied = document.execCommand('copy');
        } catch (e) {
            copied = false;
        }

        document.body.removeChild(textarea);

        if (copied) {
            showDialog('Success', textarea.value === '' ? 'Copied an empty value to clipboard.' : 'Copied to clipboard!');
        } else {
            showDialog('Error', 'Failed to copy. Please select and copy manually.');
        }
    }

    // ============================================================
    // ===== CUSTOM DIALOG =====
    // ============================================================

    function showDialog(title, message, buttons, content) {
        console.log('showDialog called with title:', title);
        
        document.getElementById('dialogTitle').textContent = title;
        document.getElementById('dialogMessage').textContent = message;
        
        var contentDiv = document.getElementById('dialogContent');
        if (content) {
            contentDiv.innerHTML = content;
            contentDiv.style.display = 'block';
            console.log('Content set, length:', content.length);
        } else {
            contentDiv.innerHTML = '';
            contentDiv.style.display = 'none';
        }
        
        var buttonsDiv = document.getElementById('dialogButtons');
        if (buttons && buttons.length > 0) {
            buttonsDiv.innerHTML = buttons.map(function(b, i) {
                return '<button class="btn ' + (b.class || 'btn-primary') + '" onclick="dialogButtonClick(' + i + ')">' + b.label + '</button>';
            }).join('');
            window._dialogCallbacks = buttons.map(function(b) { return b.callback || null; });
        } else {
            buttonsDiv.innerHTML = '<button class="btn btn-primary" onclick="closeDialog()">OK</button>';
            window._dialogCallbacks = [null];
        }
        
        var dialog = document.getElementById('customDialog');
        if (dialog) {
            dialog.style.display = 'flex';
            dialog.classList.add('active');
            console.log('Dialog overlay activated');
            
            void dialog.offsetHeight;
            
            var dialogBox = dialog.querySelector('.custom-dialog-box');
            if (dialogBox) {
                dialogBox.style.display = 'block';
                dialogBox.style.visibility = 'visible';
            }
        } else {
            console.error('Dialog overlay not found!');
        }
    }
    
    function dialogButtonClick(index) {
        var callback = window._dialogCallbacks ? window._dialogCallbacks[index] : null;
        if (callback && typeof callback === 'function') {
            callback();
        }
        closeDialog();
    }
    
    function closeDialog() {
        var dialog = document.getElementById('customDialog');
        if (dialog) {
            dialog.classList.remove('active');
            dialog.style.display = 'none';
        }
        document.getElementById('dialogContent').innerHTML = '';
        window._dialogCallbacks = null;
    }
    
    document.getElementById('customDialog').addEventListener('click', function(e) {
        if (e.target === this) closeDialog();
    });
    
    function confirmAction(title, message, callback) {
        showDialog(title, message, [
            { label: 'Cancel', class: 'btn-secondary', callback: null },
            { label: 'Confirm', class: 'btn-confirm', callback: callback }
        ]);
    }

    // ===== LEFT MENU DRAWER =====
    function openMenuDrawer() {
        var overlay = document.getElementById('menuDrawerOverlay');
        if (!overlay) return;
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
        document.body.classList.add('menu-open');
    }
    function closeMenuDrawer(event) {
        if (event && event.target !== event.currentTarget) return;
        var overlay = document.getElementById('menuDrawerOverlay');
        if (!overlay) return;
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('menu-open');
    }
    function toggleChangePasswordForm() {
        var form = document.getElementById('changePasswordForm');
        var toggle = document.getElementById('changePasswordToggle');
        if (!form || !toggle) return;
        var opening = form.style.display === 'none' || form.style.display === '';
        form.style.display = opening ? 'block' : 'none';
        toggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
        if (opening) {
            var input = document.getElementById('newPassword');
            if (input) input.focus();
        }
    }

    var changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', function(event) {
            var newPassword = document.getElementById('newPassword').value;
            var confirmPassword = document.getElementById('confirmPassword').value;
            var message = document.getElementById('passwordFormMessage');
            if (newPassword.length < 8) {
                event.preventDefault();
                message.textContent = 'Password must be at least 8 characters long.';
            } else if (newPassword !== confirmPassword) {
                event.preventDefault();
                message.textContent = 'The passwords do not match.';
            } else {
                message.textContent = '';
            }
        });
    }

    function goToDashboard() {
        closeMenuDrawer();
        var form = document.createElement('form');
        form.method = 'POST';
        var clear = document.createElement('input'); clear.type = 'hidden'; clear.name = 'clear_user'; clear.value = '1';
        form.appendChild(clear); document.body.appendChild(form); form.submit();
    }
    document.addEventListener('keydown', function(event) { if (event.key === 'Escape') closeMenuDrawer(); });

    // ============================================================
    // ===== DASHBOARD TAB SWITCHING =====
    // ============================================================

    function switchDashboardTab(tabName, btn) {
        document.querySelectorAll('.dashboard-content').forEach(function(el) { el.classList.remove('active'); });
        document.querySelectorAll('.dashboard-tab-btn').forEach(function(el) { el.classList.remove('active'); });
        document.getElementById('dash_tab_' + tabName).classList.add('active');
        if (btn) btn.classList.add('active');
        var formData = new FormData();
        formData.append('set_dashboard_view', 'true');
        formData.append('view', tabName);
        fetch(window.location.href, {
            method: 'POST',
            body: formData
        });
        if (tabName === 'all_config') {
            renderAllUsersEntries('pending', 'allUsersPendingList');
        }
    }

    function switchAllUsersConfigTab(tabName, btn) {
        document.querySelectorAll('#dash_tab_all_config .user-config-content').forEach(function(el) { el.classList.remove('active'); });
        document.querySelectorAll('#dash_tab_all_config .user-config-tab-btn').forEach(function(el) { el.classList.remove('active'); });
        var targetId = 'allusers_tab_' + tabName;
        document.getElementById(targetId).classList.add('active');
        if (btn) btn.classList.add('active');
        var listId = tabName === 'pending' ? 'allUsersPendingList' : 
                       tabName === 'completed' ? 'allUsersCompletedList' : 'allUsersAbortedList';
        renderAllUsersEntries(tabName, listId);
    }

    function renderAllUsersEntries(status, containerId) {
        var container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        var entries = allUsersEntries[status] || [];
        if (entries.length === 0) {
            container.innerHTML = '<p style="color:#6b7280; text-align:center; padding:20px;">No ' + status + ' entries found across all users.</p>';
            return;
        }
        var statusColors = {
            'pending': '#f59e0b',
            'completed': '#10b981',
            'aborted': '#ef4444'
        };
        var statusLabels = {
            'pending': 'Pending',
            'completed': 'Completed',
            'aborted': 'Aborted'
        };
        entries.forEach(function(entry, idx) {
            var div = document.createElement('div');
            div.className = 'config-item';
            var entryStatus = (entry.status || 'pending').toLowerCase();
            var username = entry._user || 'Unknown';
            var userId = entry._user_id || 0;
            var index = entry._index || 0;
            var fieldsHtml = renderEntryFields(entry, index);
            div.innerHTML = 
                '<div class="item-header">' +
                '<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
                '<span class="item-id">Entry #' + (idx + 1) + '</span>' +
                '<span class="entry-user-tag"> ' + username + '</span>' +
                '</div>' +
                '<span class="item-status" style="background: ' + (statusColors[entryStatus] || '#6b7280') + '">' + (statusLabels[entryStatus] || entryStatus) + '</span>' +
                '</div>' +
                fieldsHtml +
                '<div class="item-actions">' +
                '<form method="POST" style="display:inline;">' +
                '<input type="hidden" name="delete_entry" value="true">' +
                '<input type="hidden" name="user_id" value="' + userId + '">' +
                '<input type="hidden" name="index" value="' + index + '">' +
                '<button type="button" class="btn btn-danger btn-sm" onclick="confirmAction(\'Delete Entry\', \'Delete this entry for ' + username + '?\', function(){ this.closest(\'form\').submit(); }.bind(this))"> Delete</button>' +
                '</form>' +
                '<form method="POST" style="display:inline;">' +
                '<input type="hidden" name="update_entry_status" value="true">' +
                '<input type="hidden" name="user_id" value="' + userId + '">' +
                '<input type="hidden" name="index" value="' + index + '">' +
                '<select name="new_status" class="status-select" onchange="this.form.submit()">' +
                '<option value="pending" ' + (entryStatus === 'pending' ? 'selected' : '') + '> Pending</option>' +
                '<option value="completed" ' + (entryStatus === 'completed' ? 'selected' : '') + '> Completed</option>' +
                '<option value="aborted" ' + (entryStatus === 'aborted' ? 'selected' : '') + '> Aborted</option>' +
                '</select>' +
                '</form>' +
                '<form method="POST" style="display:inline;">' +
                '<input type="hidden" name="select_user" value="true">' +
                '<input type="hidden" name="user_id" value="' + userId + '">' +
                '<button type="submit" class="btn btn-primary btn-sm"> View Account</button>' +
                '</form>' +
                '</div>';
            container.appendChild(div);
        });
    }

    // ============================================================
    // ===== USER CONFIG TAB SWITCHING =====
    // ============================================================

    function switchUserConfigTab(tabName, btn) {
        var allowedTabs = ['add_entry', 'pending', 'completed', 'aborted'];
        if (!allowedTabs.includes(tabName)) return;

        document.querySelectorAll('.user-config-content').forEach(function(el) {
            el.classList.remove('active');
        });
        document.querySelectorAll('.user-config-tab-btn').forEach(function(el) {
            el.classList.remove('active');
        });

        var target = document.getElementById('user_tab_' + tabName);
        if (target) target.classList.add('active');
        if (btn) btn.classList.add('active');

        if (tabName === 'pending') {
            renderStatusEntries('pending', 'pendingEntriesList');
        } else if (tabName === 'completed') {
            renderStatusEntries('completed', 'completedEntriesList');
        } else if (tabName === 'aborted') {
            renderStatusEntries('aborted', 'abortedEntriesList');
        } else {
            updateSaveEntryButtonVisibility();
        }
    }

    // ============================================================
    // ===== SWITCH STATUS SUB TAB =====
    // ============================================================

    function switchStatusSubTab(status, tabId, btn) {
        var container = document.getElementById(status + 'SubTabs');
        if (container) {
            container.querySelectorAll('.dynamic-sub-tab-btn').forEach(function(el) { el.classList.remove('active'); });
            if (btn) btn.classList.add('active');
        }
        var contentContainer = document.getElementById('user_tab_' + status);
        if (contentContainer) {
            contentContainer.querySelectorAll('.dynamic-sub-tab-content').forEach(function(el) { el.classList.remove('active'); });
            var target = document.getElementById(status + 'SubTab_' + tabId);
            if (target) {
                target.classList.add('active');
            }
        }
        if (tabId === 'all_fields') {
            renderStatusEntries(status, status + 'EntriesList');
        } else {
            var tabIndex = parseInt(tabId.replace('tab_', ''));
            if (!isNaN(tabIndex)) {
                renderStatusEntriesWithFilter(status, status + 'EntriesList_tab_' + tabIndex, tabIndex);
            }
        }
    }

    // ============================================================
    // ===== RENDER STATUS ENTRIES =====
    // ============================================================

    function renderStatusEntries(status, containerId) {
        var container = document.getElementById(containerId);
        if (!container) return;
        var entries = userSettings.filter(function(entry, index) {
            var entryStatus = (entry.status || 'pending').toLowerCase();
            if (entryStatus === status) {
                entry._index = index;
                return true;
            }
            return false;
        });
        renderEntryList(entries, container, status);
    }

    function renderStatusEntriesWithFilter(status, containerId, tabIndex) {
        var container = document.getElementById(containerId);
        if (!container) return;
        var tab = userDynamicTabs[tabIndex];
        if (!tab) {
            container.innerHTML = '<p style="color:#6b7280; text-align:center; padding:20px;">Tab not found.</p>';
            return;
        }
        var displayFields = tab.dynamic_fields_display || [];
        var entries = userSettings.filter(function(entry, index) {
            var entryStatus = (entry.status || 'pending').toLowerCase();
            if (entryStatus === status) {
                entry._index = index;
                return true;
            }
            return false;
        });
        var filteredEntries = entries.map(function(entry) {
            var filtered = {};
            displayFields.forEach(function(fieldKey) {
                if (entry[fieldKey] !== undefined) {
                    filtered[fieldKey] = entry[fieldKey];
                }
            });
            filtered.status = entry.status;
            filtered.operation_status = entry.operation_status;
            filtered._index = entry._index;
            return filtered;
        });
        renderEntryList(filteredEntries, container, status);
    }

    function copyObjectValueFromAttr(button) {
        var text = button.getAttribute('data-copy-text');
        if (!text) {
            showDialog('Error', 'No text to copy');
            return;
        }
        var decodedText = text.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
        copyToClipboard(decodedText);
    }

    // ============================================================
    // ===== RENDER ENTRY FIELDS =====
    // ============================================================

    function renderEntryFields(entry, index) {
        var displayFields = Object.keys(entry).filter(function(k) {
            return k !== 'status' && k !== 'operation_status' && k !== '_user' && k !== '_user_id' && k !== '_index' && k !== '_object';
        });
        if (displayFields.length === 0) {
            return '<div class="entry-details"><p style="color:#6b7280; text-align:center; padding:10px;">No fields available</p></div>';
        }
        var html = '<div class="entry-details">';
        var flattenedGroups = {};
        var individualFields = [];
        displayFields.forEach(function(key) {
            if (key.includes('_')) {
                var parts = key.split('_');
                var mainKey = parts[0];
                var subKey = parts.slice(1).join('_');
                if (!flattenedGroups[mainKey]) {
                    flattenedGroups[mainKey] = {};
                }
                flattenedGroups[mainKey][subKey] = entry[key];
            } else {
                individualFields.push(key);
            }
        });
        var hasFlattenedGroups = Object.keys(flattenedGroups).some(function(mainKey) {
            return Object.keys(flattenedGroups[mainKey]).length > 1;
        });
        if (hasFlattenedGroups) {
            for (var mainKey in flattenedGroups) {
                var subFields = flattenedGroups[mainKey];
                var subKeys = Object.keys(subFields);
                if (subKeys.length > 0) {
                    var objectId = 'obj_' + index + '_' + mainKey;
                    html += '<div class="entry-field-group object-field" id="' + objectId + '">';
                    html += '<span class="object-label">' + mainKey + '</span>';
                    html += '<div class="sub-fields-container">';
                    subKeys.forEach(function(subKey) {
                        var subValue = subFields[subKey];
                        var displayValue = typeof subValue === 'object' ? JSON.stringify(subValue, null, 2) : subValue;
                        var escapedValue = typeof displayValue === 'string' ? displayValue.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : displayValue;
                        var rawValue = typeof subValue === 'object' ? JSON.stringify(subValue) : subValue;
                        html +=
                            '<div class="sub-field-item" data-raw-value="' + encodeURIComponent(rawValue == null ? '' : String(rawValue)) + '">' +
                            '<span class="sub-label">' + subKey + '</span>' +
                            '<div class="sub-value">' + escapedValue + '</div>' +
                            '</div>';
                    });
                    html += '</div>';
                    var combinedText = subKeys.map(function(sk) {
                        var val = subFields[sk];
                        return typeof val === 'object' ? JSON.stringify(val) : val;
                    }).filter(function(v) { return v && v !== '' && v !== '{}'; }).join('\n');
                    html += '</div>';
                }
            }
        }
        displayFields.forEach(function(key) {
            var value = entry[key];
            if (key.includes('_')) {
                var parts = key.split('_');
                var mainKey = parts[0];
                if (flattenedGroups[mainKey] && Object.keys(flattenedGroups[mainKey]).length > 1) {
                    return;
                }
            }
            var isObjectField = (
                (typeof value === 'object' && 
                value !== null && 
                !Array.isArray(value) && 
                value.hasOwnProperty('_object') && 
                value._object === true)
                ||
                (typeof value === 'object' && 
                value !== null && 
                !Array.isArray(value) && 
                Object.keys(value).length > 0 && 
                !value.hasOwnProperty('_object'))
            );
            if (isObjectField) {
                var objectData = value;
                var subKeys = Object.keys(objectData).filter(function(k) { return k !== '_object'; });
                var objectId = 'obj_' + index + '_' + key;
                html += '<div class="entry-field-group object-field" id="' + objectId + '">';
                html += '<span class="object-label">' + key + '</span>';
                html += '<div class="sub-fields-container">';
                if (subKeys.length > 0) {
                    subKeys.forEach(function(subKey) {
                        var subValue = objectData[subKey];
                        var displayValue = typeof subValue === 'object' ? JSON.stringify(subValue, null, 2) : subValue;
                        var escapedValue = typeof displayValue === 'string' ?
                            displayValue.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') :
                            displayValue;
                        var rawValue = typeof subValue === 'object' ? JSON.stringify(subValue) : subValue;
                        html +=
                            '<div class="sub-field-item" data-raw-value="' + encodeURIComponent(rawValue == null ? '' : String(rawValue)) + '">' +
                            '<span class="sub-label">' + subKey + '</span>' +
                            '<div class="sub-value">' + escapedValue + '</div>' +
                            '</div>';
                    });
                } else {
                    html += 
                        '<div class="sub-field-item">' +
                        '<span class="sub-label">No sub-fields</span>' +
                        '<span class="sub-value">-</span>' +
                        '</div>';
                }
                html += '</div>';
                var combinedText = subKeys.map(function(sk) {
                    var val = objectData[sk];
                    return typeof val === 'object' ? JSON.stringify(val) : val;
                }).filter(function(v) { return v && v !== '' && v !== '{}'; }).join('\n');
                html += '</div>';
            } else if (!key.includes('_') || !hasFlattenedGroups) {
                var displayValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
                var escapedValue = typeof displayValue === 'string' ? displayValue.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : displayValue;
                var rawValue = typeof value === 'object' ? JSON.stringify(value) : value;
                var fieldId = 'field_' + index + '_' + key;
                html +=
                    '<div class="entry-field-group individual-field" id="' + fieldId + '" data-raw-value="' + encodeURIComponent(rawValue == null ? '' : String(rawValue)) + '">' +
                    '<span class="field-label">' + key + '</span>' +
                    '<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">' +
                    '<div class="field-value" style="flex:1;min-width:0;">' + escapedValue + '</div>' +
                    '<button class="btn btn-secondary btn-sm" onclick="copyIndividualFromDiv(\'' + fieldId + '\')">📋 Copy</button>' +
                    '</div>' +
                    '</div>';
            }
        });
        html += '</div>';
        return html;
    }

    function copyIndividualFromDiv(elementId) {
        var container = document.getElementById(elementId);
        if (!container) {
            showDialog('Error', 'Field not found');
            return;
        }
        var rawValue = container.getAttribute('data-raw-value');
        if (!rawValue) {
            showDialog('Info', 'No value to copy');
            return;
        }
        var textToCopy = decodeURIComponent(rawValue);
        if (textToCopy.trim().startsWith('{') || textToCopy.trim().startsWith('[')) {
            try {
                var parsed = JSON.parse(textToCopy);
                textToCopy = JSON.stringify(parsed, null, 2);
            } catch(e) {}
        }
        if (!textToCopy || textToCopy.trim() === '') {
            showDialog('Info', 'No value to copy');
            return;
        }
        copyToClipboard(textToCopy);
    }

    function copyObjectValuesFromDiv(containerId) {
        var container = document.getElementById(containerId);
        if (!container) {
            showDialog('Error', 'Object container not found');
            return;
        }
        var subItems = container.querySelectorAll('.sub-field-item');
        if (subItems.length === 0) {
            showDialog('Info', 'No sub-fields to copy');
            return;
        }
        var copyTexts = [];
        subItems.forEach(function(item) {
            var rawValue = item.getAttribute('data-raw-value');
            if (rawValue) {
                var value = decodeURIComponent(rawValue);
                if (value.trim().startsWith('{') || value.trim().startsWith('[')) {
                    try {
                        var parsed = JSON.parse(value);
                        value = JSON.stringify(parsed, null, 2);
                    } catch(e) {}
                }
                if (value && value.trim() !== '' && value.trim() !== '{}') {
                    copyTexts.push(value);
                }
            }
        });
        if (copyTexts.length === 0) {
            showDialog('Info', 'No values to copy');
            return;
        }
        var textToCopy = copyTexts.join('\n');
        copyToClipboard(textToCopy);
    }

    function renderEntryList(entries, container, status) {
        container.innerHTML = '';
        if (entries.length === 0) {
            container.innerHTML = '<p style="color:#6b7280; text-align:center; padding:20px;">No ' + status + ' entries found.</p>';
            return;
        }
        var statusColors = {
            'pending': '#f59e0b',
            'completed': '#10b981',
            'aborted': '#ef4444'
        };
        var statusLabels = {
            'pending': 'Pending',
            'completed': 'Completed',
            'aborted': 'Aborted'
        };
        entries.forEach(function(entry) {
            var div = document.createElement('div');
            div.className = 'config-item';
            var index = entry._index;
            var entryStatus = (entry.status || 'pending').toLowerCase();
            var fieldsHtml = renderEntryFields(entry, index);
            div.innerHTML = 
                '<div class="item-header">' +
                '<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">' +
                '<span class="item-id">Entry #' + (index + 1) + '</span>' +
                '</div>' +
                '<span class="item-status" style="background: ' + (statusColors[entryStatus] || '#6b7280') + '">' + (statusLabels[entryStatus] || entryStatus) + '</span>' +
                '</div>' +
                fieldsHtml +
                '<div class="item-actions">' +
                '<form method="POST" style="display:inline;">' +
                '<input type="hidden" name="delete_entry" value="true">' +
                '<input type="hidden" name="user_id" value="' + selectedUserId + '">' +
                '<input type="hidden" name="index" value="' + index + '">' +
                '<button type="button" class="btn btn-danger btn-sm" onclick="confirmAction(\'Delete Entry\', \'Delete this entry?\', function(){ this.closest(\'form\').submit(); }.bind(this))"> Delete</button>' +
                '</form>' +
                '<form method="POST" style="display:inline;">' +
                '<input type="hidden" name="update_entry_status" value="true">' +
                '<input type="hidden" name="user_id" value="' + selectedUserId + '">' +
                '<input type="hidden" name="index" value="' + index + '">' +
                '<select name="new_status" class="status-select" onchange="this.form.submit()">' +
                '<option value="pending" ' + (entryStatus === 'pending' ? 'selected' : '') + '> Pending</option>' +
                '<option value="completed" ' + (entryStatus === 'completed' ? 'selected' : '') + '> Completed</option>' +
                '<option value="aborted" ' + (entryStatus === 'aborted' ? 'selected' : '') + '> Aborted</option>' +
                '</select>' +
                '</form>' +
                '</div>';
            container.appendChild(div);
        });
    }

    // ============================================================
    // ===== SWITCH NEW PROJECT SUB TAB =====
    // ============================================================

    // Show Save Entry only when the currently displayed main tab is enabled
    // in Submit Tabs. Nested child tabs inherit their parent tab's setting.
    function updateSaveEntryButtonVisibility() {
        var saveButton = document.getElementById('saveEntryButton');
        if (!saveButton) return;

        var activeContent = document.querySelector('#user_tab_add_entry .dynamic-sub-tab-content.active');
        var enabled = false;

        if (activeContent && activeContent.id !== 'newProjectSubTab_all_fields') {
            var tabId = activeContent.id.replace('newProjectSubTab_', '');
            var tabButton = document.querySelector('#user_tab_add_entry #newProjectSubTabs .dynamic-sub-tab-btn[data-tab="' + tabId + '"]');
            enabled = !!(tabButton && tabButton.getAttribute('data-submit-enabled') === '1');
        }

        saveButton.style.display = enabled ? 'inline-flex' : 'none';
    }

    function switchNewProjectNestedSubTab(btn) {
        var wrapper = btn.closest('.nested-project-tabs');
        if (!wrapper) return;
        wrapper.querySelectorAll('.nested-child-btn').forEach(function(b) { b.classList.remove('active'); });
        wrapper.querySelectorAll('.nested-child-content').forEach(function(c) { c.classList.remove('active'); c.style.display = 'none'; });
        btn.classList.add('active');
        var index = Array.prototype.indexOf.call(wrapper.querySelectorAll('.nested-child-btn'), btn);
        var contents = wrapper.querySelectorAll('.nested-child-content');
        if (contents[index]) { contents[index].classList.add('active'); contents[index].style.display = 'block'; }
        updateSaveEntryButtonVisibility();
    }

    function switchNewProjectSubTab(tabId, btn) {
        document.querySelectorAll('#user_tab_add_entry .dynamic-sub-tab-content').forEach(function(el) { el.classList.remove('active'); });
        document.querySelectorAll('#user_tab_add_entry #newProjectSubTabs .dynamic-sub-tab-btn').forEach(function(el) { el.classList.remove('active'); });
        var target = document.getElementById('newProjectSubTab_' + tabId);
        if (target) {
            target.classList.add('active');
            // Selecting a main tab always starts on its first child sub-tab.
            var nested = target.querySelector('.nested-project-tabs');
            if (nested) {
                var childButtons = nested.querySelectorAll('.nested-child-btn');
                var childContents = nested.querySelectorAll('.nested-child-content');
                childButtons.forEach(function(childButton, index) {
                    childButton.classList.toggle('active', index === 0);
                });
                childContents.forEach(function(childContent, index) {
                    childContent.classList.toggle('active', index === 0);
                    childContent.style.display = index === 0 ? 'block' : 'none';
                });
            }
        }
        if (btn) btn.classList.add('active');
        updateSaveEntryButtonVisibility();
    }

    // ============================================================
    // ===== SUBMIT USER ENTRY =====
    // ============================================================

    document.addEventListener('DOMContentLoaded', function() {
        updateSaveEntryButtonVisibility();
    });

    function submitUserEntry() {
        var activeContent = document.querySelector('#user_tab_add_entry .dynamic-sub-tab-content.active');
        if (!activeContent) {
            showDialog('Error', 'No active form found.');
            return;
        }
        updateSaveEntryButtonVisibility();
        var saveButton = document.getElementById('saveEntryButton');
        if (!saveButton || saveButton.style.display === 'none') {
            showDialog('Info', 'Saving entries is disabled for the currently displayed tab in Submit Tabs.');
            return;
        }
        var inputs = activeContent.querySelectorAll('input, textarea, select');
        var entryData = {};
        var objectContainers = activeContent.querySelectorAll('[id^="object_"]');
        inputs.forEach(function(input) {
            if (input.id && input.id.startsWith('entry_')) {
                var key = input.id.replace('entry_', '');
                if (key.includes('_date') || key.includes('_hour_12') || key.includes('_minute_12') || key.includes('_ampm')) {
                    return;
                }
                    entryData[key] = input.value;
            }
        });
        objectContainers.forEach(function(container) {
            var objectKey = container.id.replace('object_', '').replace('_container', '');
            var subInputs = container.querySelectorAll('input, textarea, select');
            var objectData = {};
            objectData['_object'] = true;
            subInputs.forEach(function(input) {
                if (input.id && input.id.startsWith('entry_' + objectKey + '_')) {
                    var subKey = input.id.replace('entry_' + objectKey + '_', '');
                    if (subKey.includes('_date') || subKey.includes('_hour_12') || subKey.includes('_minute_12') || subKey.includes('_ampm')) {
                        return;
                    }
                    objectData[subKey] = input.value;
                }
            });
            var hasData = Object.keys(objectData).some(function(k) { return k !== '_object' && objectData[k] !== ''; });
            if (hasData) {
                entryData[objectKey] = objectData;
            }
        });
        var hasData = Object.values(entryData).some(function(v) {
            if (typeof v === 'object') {
                return Object.values(v).some(function(sv) { return sv !== '' && sv !== '_object'; });
            }
            return v !== '';
        });
        if (!hasData) {
            showDialog('Error', 'Please enter at least one field value.');
            return;
        }
        document.getElementById('entryDataInput').value = JSON.stringify(entryData);
        document.getElementById('addEntryForm').submit();
    }

    // Legacy renderer retained for compatibility with account-scoped field editor helpers.
    // The global dashboard Dynamic Fields tab has been removed.
    function openUserSearchDialog() {
        document.getElementById('userSearchDialog').classList.add('active');
        document.getElementById('userSearchInput').value = '';
        document.querySelectorAll('#userSearchResults .user-search-item').forEach(function(item) {
            item.style.display = 'block';
        });
        setTimeout(function() { document.getElementById('userSearchInput').focus(); }, 100);
    }

    function closeUserSearchDialog() {
        document.getElementById('userSearchDialog').classList.remove('active');
    }

    function filterUserSearch() {
        var query = document.getElementById('userSearchInput').value.toLowerCase().trim();
        var items = document.querySelectorAll('#userSearchResults .user-search-item');
        items.forEach(function(item) {
            var name = item.getAttribute('data-user-name') || '';
            var email = item.getAttribute('data-user-email') || '';
            var match = name.includes(query) || email.includes(query);
            item.style.display = match ? 'block' : 'none';
        });
    }

    function selectUserFromSearch(userId) {
        var form = document.createElement('form');
        form.method = 'POST';
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'select_user';
        input.value = 'true';
        var input2 = document.createElement('input');
        input2.type = 'hidden';
        input2.name = 'user_id';
        input2.value = userId;
        form.appendChild(input);
        form.appendChild(input2);
        document.body.appendChild(form);
        form.submit();
    }

    document.getElementById('userSearchDialog').addEventListener('click', function(e) {
        if (e.target === this) closeUserSearchDialog();
    });

    // ============================================================
    // ===== SYNC ON INPUT =====
    // ============================================================

    document.addEventListener('input', function(e) {
        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (addEntryTab && addEntryTab.contains(e.target)) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                syncFieldValues();
            }
        }
    });

    document.addEventListener('paste', function(e) {
        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (addEntryTab && addEntryTab.contains(e.target)) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                setTimeout(function() { syncFieldValues(); }, 100);
            }
        }
    });
    // ============================================================
    // ===== TRANSCRIPT DETECTION AND CONVERSION ENGINE =====
    // ============================================================

   
</script>
<script>
    // ============================================================
    // ===== COPY BUTTON VISIBILITY BASED ON TAB FEATURES =====
    // ============================================================

    // Function to update copy button visibility based on active tab
    function updateCopyButtonsVisibility() {
        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (!addEntryTab) return;
        
        var activeContent = addEntryTab.querySelector('.dynamic-sub-tab-content.active');
        if (!activeContent) return;
        
        // Find the active tab
        var activeTabBtn = document.querySelector('#user_tab_add_entry .dynamic-sub-tab-btn.active');
        var tabId = null;
        if (activeTabBtn) {
            tabId = activeTabBtn.getAttribute('data-tab');
            if (!tabId) {
                var onclickAttr = activeTabBtn.getAttribute('onclick');
                if (onclickAttr) {
                    var match = onclickAttr.match(/switchNewProjectSubTab\('([^']+)'/);
                    if (match) tabId = match[1];
                }
            }
        }
        
        var tabIndex = -1;
        if (tabId) {
            tabIndex = parseInt(tabId.replace('tab_', ''));
        }
        
        // Check if we're on the all_fields tab
        var allFieldsTab = document.getElementById('newProjectSubTab_all_fields');
        if (allFieldsTab && allFieldsTab.classList.contains('active')) {
            // On all_fields tab, show all copy buttons by default
            activeContent.querySelectorAll('[id^="field_"]_container .btn-secondary, [id^="object_"]_container .btn-secondary').forEach(function(btn) {
                if (btn.textContent.includes('Copy')) {
                    btn.style.display = 'inline-block';
                }
            });
            return;
        }
        
        if (isNaN(tabIndex) || tabIndex < 0 || tabIndex >= userDynamicTabs.length) {
            // Default: show all copy buttons
            activeContent.querySelectorAll('[id^="field_"]_container .btn-secondary, [id^="object_"]_container .btn-secondary').forEach(function(btn) {
                if (btn.textContent.includes('Copy')) {
                    btn.style.display = 'inline-block';
                }
            });
            return;
        }
        
        var tab = userDynamicTabs[tabIndex];
        if (!tab) {
            // Default: show all copy buttons
            activeContent.querySelectorAll('[id^="field_"]_container .btn-secondary, [id^="object_"]_container .btn-secondary').forEach(function(btn) {
                if (btn.textContent.includes('Copy')) {
                    btn.style.display = 'inline-block';
                }
            });
            return;
        }
        
        var additionalFeatures = tab.additional_features || {
            copy_button: false,
            transcript_detection: false,
            transcript_with_structured_data_detection: false
        };
        
        var copyButtonEnabled = additionalFeatures.copy_button === true;
        
        // Find all copy buttons in the active content
        var copyButtons = activeContent.querySelectorAll('.btn-secondary');
        activeContent.querySelectorAll('.individual-sentence-copy-button').forEach(function(btn) {
            btn.style.display = 'inline-flex';
        });
        copyButtons.forEach(function(btn) {
            // Individual-sentence rows always keep their own Copy button.
            // The tab-level copy_button feature controls only general field/object copy buttons.
            if (btn.classList.contains('individual-sentence-copy-button')) {
                btn.style.display = 'inline-flex';
                return;
            }
            // Check if this is a copy button (contains copy-related text)
            var btnText = btn.textContent || '';
            if (btnText.includes('Copy') || btnText.includes('📋')) {
                if (copyButtonEnabled) {
                    btn.style.display = 'inline-block';
                } else {
                    btn.style.display = 'none';
                }
            }
        });
        
        // Also handle the copy buttons inside field containers
        activeContent.querySelectorAll('[id^="field_"]_container .btn-secondary, [id^="object_"]_container .btn-secondary').forEach(function(btn) {
            if (btn.classList.contains('individual-sentence-copy-button')) {
                btn.style.display = 'inline-flex';
                return;
            }
            var btnText = btn.textContent || '';
            if (btnText.includes('Copy') || btnText.includes('📋')) {
                if (copyButtonEnabled) {
                    btn.style.display = 'inline-block';
                } else {
                    btn.style.display = 'none';
                }
            }
        });
    }

    // Override switchNewProjectSubTab to also update copy buttons
    var _originalSwitchNewProjectSubTab2 = switchNewProjectSubTab;
    switchNewProjectSubTab = function(tabId, btn) {
        _originalSwitchNewProjectSubTab2(tabId, btn);
        setTimeout(function() { 
            detectTranscripts();
            updateCopyButtonsVisibility();
        }, 200);
    };

    // Run copy button visibility check after DOM changes
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            updateCopyButtonsVisibility();
        }, 500);
    });

    console.log('✅ Copy button visibility based on tab features initialized');
</script>
<script>
    // ============================================================
    // ===== TRANSCRIPT DETECTION AND CONVERSION ENGINE =====
    // ============================================================

    // Store transcript data for each element
    window._transcriptData = {};

    // Store character data from the separate element
    window._characterData = null;

    // Store conversion results for each element
    window._conversionResults = {};

    // Function to get the currently active tab index
    function getActiveTabIndex() {
        var activeTabBtn = document.querySelector('#user_tab_add_entry .dynamic-sub-tab-btn.active');
        if (!activeTabBtn) return -1;
        
        var tabId = activeTabBtn.getAttribute('data-tab');
        if (!tabId) {
            var onclickAttr = activeTabBtn.getAttribute('onclick');
            if (onclickAttr) {
                var match = onclickAttr.match(/switchNewProjectSubTab\('([^']+)'/);
                if (match) tabId = match[1];
            }
        }
        
        if (!tabId) return -1;
        var tabIndex = parseInt(tabId.replace('tab_', ''));
        return isNaN(tabIndex) ? -1 : tabIndex;
    }

    // Get feature flags for the currently active New Project tab, including nested tabs.
    function getActiveTabFeatures() {
        var enabledDefaults = {
            copy_button: true,
            transcript_detection: true,
            transcript_with_structured_data_detection: true
        };

        function normalizeFeatures(tab) {
            var f = (tab && tab.additional_features) || {};
            return {
                copy_button: f.copy_button === true,
                transcript_detection: f.transcript_detection === true,
                transcript_with_structured_data_detection: f.transcript_with_structured_data_detection === true
            };
        }

        // The All Fields view intentionally enables all three helpers.
        var allFieldsButton = document.getElementById('newProjectSubTabBtn_all_fields') ||
                              document.getElementById('newProjectSubTab_all_fields');
        if ((allFieldsButton && allFieldsButton.classList.contains('active')) ||
            (document.getElementById('newProjectSubTab_all_fields') &&
             document.getElementById('newProjectSubTab_all_fields').classList.contains('active'))) {
            return enabledDefaults;
        }

        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (!addEntryTab) return enabledDefaults;

        // Resolve the actual visible content first. Root content IDs are rendered as
        // newProjectSubTab_tab_N, where N is the index in userDynamicTabs.
        var activeRootContent = addEntryTab.querySelector('.dynamic-sub-tab-content.active');
        if (activeRootContent) {
            var rootMatch = (activeRootContent.id || '').match(/^newProjectSubTab_tab_(\d+)$/);
            if (rootMatch) {
                var rootIndex = parseInt(rootMatch[1], 10);
                var rootTab = userDynamicTabs && userDynamicTabs[rootIndex];

                if (rootTab) {
                    // Nested child tabs have no IDs/data attributes in the markup.
                    // Their position in the active wrapper maps directly to sub_tabs.
                    var activeChildContent = activeRootContent.querySelector('.nested-child-content.active');
                    var activeNestedWrapper = activeChildContent ? activeChildContent.closest('.nested-project-tabs') : null;

                    if (activeChildContent && activeNestedWrapper && Array.isArray(rootTab.sub_tabs)) {
                        var visibleChildContents = Array.prototype.slice.call(
                            activeNestedWrapper.querySelectorAll('.nested-child-content')
                        );
                        var childIndex = visibleChildContents.indexOf(activeChildContent);
                        var visibleChildButtons = Array.prototype.slice.call(
                            activeNestedWrapper.querySelectorAll('.nested-child-btn')
                        );
                        var activeChildButton = activeNestedWrapper.querySelector('.nested-child-btn.active');

                        if (childIndex < 0 && activeChildButton) {
                            childIndex = visibleChildButtons.indexOf(activeChildButton);
                        }

                        // PHP filters hidden children before rendering, so map by the
                        // displayed child order, matching the rendered child content.
                        var displayedChildren = rootTab.sub_tabs.filter(function(child) {
                            return !Object.prototype.hasOwnProperty.call(child, 'display_tab') || !!child.display_tab;
                        });
                        if (childIndex >= 0 && displayedChildren[childIndex]) {
                            return normalizeFeatures(displayedChildren[childIndex]);
                        }
                    }

                    // A root without a nested active child uses the root's own features.
                    return normalizeFeatures(rootTab);
                }
            }
        }

        // Fallback for legacy/All Fields layouts.
        var activeButton = addEntryTab.querySelector('#newProjectSubTabs .dynamic-sub-tab-btn.active');
        if (activeButton) {
            var onclick = activeButton.getAttribute('onclick') || '';
            var match = onclick.match(/switchNewProjectSubTab\(['"]tab_(\d+)['"]/);
            if (match && userDynamicTabs && userDynamicTabs[parseInt(match[1], 10)]) {
                return normalizeFeatures(userDynamicTabs[parseInt(match[1], 10)]);
            }
        }

        return enabledDefaults;
    }

    // Detect if character data is in structured JSON format with improved detection
    function detectStructuredCharacterData(text) {
        if (!text || typeof text !== 'string') return false;
        
        try {
            // Structured JSON only requires a script array or object.
            // characters_visual_prompts is optional and is not generated.
            var hasScriptArray = text.match(/"script"\s*:\s*\[/);
            var hasScriptObject = text.match(/"script"\s*:\s*\{/);

            if (hasScriptArray !== null || hasScriptObject !== null) {
                return true;
            }

            // Fallback: try to find the JSON object and validate it
            var jsonStart = text.indexOf('{');
            if (jsonStart !== -1) {
                var braceCount = 0;
                var jsonEnd = -1;
                for (var i = jsonStart; i < text.length; i++) {
                    if (text[i] === '{') braceCount++;
                    else if (text[i] === '}') {
                        braceCount--;
                        if (braceCount === 0) {
                            jsonEnd = i + 1;
                            break;
                        }
                    }
                }
                if (jsonEnd !== -1) {
                    var jsonStr = text.substring(jsonStart, jsonEnd);
                    var parsed = JSON.parse(jsonStr);
                    if (parsed.script) {
                        return true;
                    }
                }
            }
            
            return false;
        } catch (e) {
            return false;
        }
    }

    // Shared feature-flag normalizer. Keep it global so transcript scanning and
    // conversion actions can use the owning field's configured feature flags.
    function sceneIQFeatureEnabled(value) {
        return value === true || value === 1 || value === '1' ||
            (typeof value === 'string' && ['true', 'yes', 'on', 'enabled'].indexOf(value.trim().toLowerCase()) !== -1);
    }

    // Detect transcripts across rendered dynamic-tab fields, including fields inside
    // inactive tabs. Inactive tab panels are often display:none, so scanning only the
    // active child panel misses the conversion field entirely.
    function detectTranscripts() {
        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (!addEntryTab) {
            console.debug('[SceneIQ Transcript Detection] Not run: #user_tab_add_entry was not found.');
            return;
        }

        function tabDetailsForElement(element) {
            var rootContent = element.closest('.dynamic-sub-tab-content');
            var rootIndexMatch = rootContent && (rootContent.id || '').match(/^newProjectSubTab_tab_(\d+)$/);
            var rootIndex = rootIndexMatch ? parseInt(rootIndexMatch[1], 10) : -1;
            var rootTab = rootIndex >= 0 && Array.isArray(userDynamicTabs) ? userDynamicTabs[rootIndex] : null;
            var rootName = rootTab ? (rootTab.tab_name || rootTab.name || '') : '';
            var childContent = element.closest('.nested-child-content');
            var childName = '';
            var tabConfig = rootTab;

            if (childContent && rootTab && Array.isArray(rootTab.sub_tabs)) {
                var wrapper = childContent.closest('.nested-project-tabs');
                var contents = wrapper ? Array.prototype.slice.call(wrapper.querySelectorAll('.nested-child-content')) : [];
                var childIndex = contents.indexOf(childContent);
                var displayedChildren = rootTab.sub_tabs.filter(function(child) {
                    return !Object.prototype.hasOwnProperty.call(child, 'display_tab') || !!child.display_tab;
                });
                if (childIndex >= 0 && displayedChildren[childIndex]) {
                    tabConfig = displayedChildren[childIndex];
                    childName = tabConfig.tab_name || tabConfig.name || '';
                }
            }

            var f = (tabConfig && tabConfig.additional_features) || {};
            // Use the shared top-level normalizer here. The similarly named
            // featureIsEnabled() inside getActiveTabFeatures() is locally scoped
            // and cannot be called from this function; doing so previously threw
            // a ReferenceError and aborted the entire transcript scan.
            var features = {
                copy_button: sceneIQFeatureEnabled(f.copy_button),
                transcript_detection: sceneIQFeatureEnabled(f.transcript_detection),
                transcript_with_structured_data_detection: sceneIQFeatureEnabled(f.transcript_with_structured_data_detection)
            };
            var dedicated = /convert.*(transcrib|json)|(transcrib|json).*convert|to\s*json/i.test(rootName + ' ' + childName);
            return {
                root_index: rootIndex,
                root_name: rootName,
                child_name: childName || null,
                root_content_id: rootContent ? rootContent.id : null,
                features: features,
                dedicated: dedicated
            };
        }

        var activeRoot = addEntryTab.querySelector('.dynamic-sub-tab-content.active');
        var activeChild = activeRoot ? activeRoot.querySelector('.nested-child-content.active') : null;
        var activeRootButton = addEntryTab.querySelector('#newProjectSubTabs .dynamic-sub-tab-btn.active');
        var activeChildButton = activeChild && activeChild.closest('.nested-project-tabs')
            ? activeChild.closest('.nested-project-tabs').querySelector('.nested-child-btn.active') : null;

        // Scan all configured tab panels, not only the currently active panel. This
        // also detects text already present in a hidden conversion field before the
        // user switches to that tab; hidden controls are not excluded from detection.
        var allElements = Array.prototype.slice.call(addEntryTab.querySelectorAll(
            'textarea, input, [contenteditable="true"], [contenteditable=""], [role="textbox"], .ql-editor'
        ));
        var elements = allElements.filter(function(el) {
            var type = (el.getAttribute('type') || '').toLowerCase();
            if (el.tagName === 'INPUT' && ['hidden', 'button', 'submit', 'reset', 'checkbox', 'radio', 'file', 'image'].indexOf(type) !== -1) return false;
            // Only fields belonging to a configured dynamic root or child are relevant.
            return !!el.closest('.dynamic-sub-tab-content');
        });

        var activeRootName = activeRootButton ? (activeRootButton.textContent || '').trim() : '(no active root button)';
        var activeChildName = activeChildButton ? (activeChildButton.textContent || '').trim() : null;
        var activeFeatures = (typeof getActiveTabFeatures === 'function') ? getActiveTabFeatures() : {};
        var report = {
            event: 'scan',
            active_root_id: activeRoot ? activeRoot.id : null,
            active_root_name: activeRootName,
            active_child_found: !!activeChild,
            active_child_name: activeChildName,
            feature_flags: {
                transcript_detection: sceneIQFeatureEnabled(activeFeatures.transcript_detection),
                structured_data_detection: sceneIQFeatureEnabled(activeFeatures.transcript_with_structured_data_detection),
                copy_button: sceneIQFeatureEnabled(activeFeatures.copy_button)
            },
            visible_fields_scanned: elements.length,
            fields_scanned_across_tabs: true,
            dedicated_conversion_tab: /convert.*(transcrib|json)|(transcrib|json).*convert|to\s*json/i.test(activeRootName + ' ' + (activeChildName || '')),
            fields: [],
            timestamped_fields: [],
            matches: []
        };

        elements.forEach(function(element, elementIndex) {
            var value = typeof element.value === 'string' ? element.value : (element.innerText || element.textContent || '');
            var fieldId = element.id || '';
            var fieldKey = element.getAttribute('name') || element.getAttribute('data-field-key') || '';
            var labelEl = element.labels && element.labels.length ? element.labels[0] : null;
            var labelText = labelEl ? labelEl.textContent.trim() : '';
            if (!fieldId) {
                fieldId = 'sceneiq_transcript_field_' + elementIndex;
                element.id = fieldId;
            }

            var tabDetails = tabDetailsForElement(element);
            var transcriptEnabled = !!tabDetails.features.transcript_detection;
            var structuredEnabled = !!tabDetails.features.transcript_with_structured_data_detection;
            var copyEnabled = !!tabDetails.features.copy_button;
            var dedicatedConversionTab = !!tabDetails.dedicated;
            var normalizedValue = value.replace(/[０-９]/g, function(ch) {
                return String.fromCharCode(ch.charCodeAt(0) - 0xFEE0);
            });
            var timestampMatches = normalizedValue.match(/(?:^|[^\d])\(?\s*\d{1,2}:\d{2}(?:\:\d{2})?\s*\)?/gm) || [];
            var hasTime = timestampMatches.length > 0;
            var hasStructuredData = typeof detectStructuredCharacterData === 'function' && detectStructuredCharacterData(value);
            var shouldShowTranscript = (hasTime && transcriptEnabled) ||
                (hasStructuredData && structuredEnabled) ||
                (dedicatedConversionTab && transcriptEnabled && value.trim().length > 0);
            var elementId = fieldId + '__transcript__' + (tabDetails.root_content_id || 'active_root') + '__' + elementIndex;

            var fieldReport = {
                id: fieldId,
                name: fieldKey,
                label: labelText,
                tab_name: tabDetails.root_name,
                child_tab_name: tabDetails.child_name,
                root_content_id: tabDetails.root_content_id,
                element_type: element.tagName.toLowerCase(),
                characters: value.length,
                has_timestamp: hasTime,
                timestamp_matches: timestampMatches.length,
                has_structured_data: hasStructuredData,
                enabled_for_transcript_detection: transcriptEnabled,
                dedicated_conversion_tab: dedicatedConversionTab,
                should_show_convert_action: shouldShowTranscript,
                preview: value.slice(0, 180)
            };
            report.fields.push(fieldReport);
            if (hasTime) {
                report.timestamped_fields.push({
                    id: fieldId,
                    tab_name: tabDetails.root_name,
                    child_tab_name: tabDetails.child_name,
                    timestamp_matches: timestampMatches.length,
                    transcript_detection_enabled: transcriptEnabled,
                    convert_json_button_expected: transcriptEnabled,
                    preview: value.slice(0, 180)
                });
            }

            var existingIndicator = document.getElementById('transcript_indicator_' + elementId);
            var existingResult = document.getElementById('transcript_result_' + elementId);

            if (!shouldShowTranscript) {
                if (existingIndicator) existingIndicator.remove();
                if (existingResult) existingResult.remove();
                if (window._transcriptData) delete window._transcriptData[elementId];
                if (window._conversionResults) delete window._conversionResults[elementId];
                return;
            }

            window._transcriptData = window._transcriptData || {};
            window._conversionResults = window._conversionResults || {};
            window._transcriptData[elementId] = { value: value, element: element, features: tabDetails.features, tabDetails: tabDetails };
            if (typeof detectCharacterData === 'function') detectCharacterData();

            var indicator = existingIndicator;
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'transcript_indicator_' + elementId;
                indicator.className = 'sceneiq-transcript-detection-indicator';
                indicator.style.cssText = 'margin-top:8px;padding:8px 12px;background:#d1fae5;border-radius:8px;border-left:4px solid #00695c;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;';
                var container = element.closest('.form-group') || element.closest('.sub-field-group') || element.parentElement;
                if (container) container.appendChild(indicator);
                else if (element.parentNode) element.parentNode.insertBefore(indicator, element.nextSibling);
            }

            var label = hasStructuredData && structuredEnabled
                ? '📝 Structured JSON Data Detected'
                : (hasTime ? '📝 Timestamped Transcript Detected (' + timestampMatches.length + ' timestamp matches)' : '📝 Transcript Text Detected');
            var elementIdArg = "'" + elementId.replace(/\\/g, "\\\\").replace(/'/g, "\\'") + "'";
            var buttonsHtml = '<div style="display:flex;gap:8px;flex-wrap:wrap;">';

            if (transcriptEnabled && value.trim().length > 0 && (hasTime || dedicatedConversionTab)) {
                buttonsHtml += '<button type="button" class="btn btn-success btn-sm sceneiq-convert-json-button" onclick="convertAndDisplayInline(' +
                    elementIdArg +
                    ')" style="padding:5px 12px;font-size:12px;">🔄 Convert to JSON</button>';
                buttonsHtml += '<button type="button" class="btn btn-primary btn-sm" onclick="openTranscriptDialog(' +
                    elementIdArg +
                    ')" style="padding:5px 12px;font-size:12px;">View Transcript</button>';
            } else if (hasStructuredData && structuredEnabled) {
                buttonsHtml += '<button type="button" class="btn btn-primary btn-sm" onclick="convertToText(' +
                    elementIdArg +
                    ')" style="padding:5px 12px;font-size:12px;">📄 Convert to Text</button>';
            }
            if (copyEnabled && !dedicatedConversionTab) {
                buttonsHtml += '<button type="button" class="btn btn-secondary btn-sm" onclick="copyTranscriptValue(' +
                    elementIdArg +
                    ')" style="padding:5px 12px;font-size:12px;">📋 Copy Transcript</button>';
            }
            buttonsHtml += '</div>';
            indicator.innerHTML = '<span style="color:#065f46;font-weight:600;">' + label + '</span>' + buttonsHtml;
            indicator.style.display = 'flex';

            report.matches.push({
                id: fieldId,
                detection_key: elementId,
                tab_name: tabDetails.root_name,
                child_tab_name: tabDetails.child_name,
                timestamp_matches: timestampMatches.length,
                label: labelText,
                preview: value.slice(0, 180)
            });
        });

        var signature = JSON.stringify({
            root: report.active_root_id,
            rootName: report.active_root_name,
            fields: report.fields.map(function(f) {
                return [f.id, f.tab_name, f.child_tab_name, f.characters, f.has_timestamp, f.timestamp_matches, f.should_show_convert_action];
            }),
            matches: report.matches.map(function(m) { return [m.id, m.timestamp_matches, m.tab_name]; })
        });

        window._sceneIQTranscriptLastScan = report;
        if (window._sceneIQLastTranscriptDebugSignature !== signature) {
            window._sceneIQLastTranscriptDebugSignature = signature;
            console.groupCollapsed('%c[SceneIQ Transcript Detection] Scan report', 'color:#00695c;font-weight:bold;');
            console.info('ACTIVE TAB / FEATURE STATUS', {
                root_tab: report.active_root_name,
                child_tab: report.active_child_name,
                active_feature_flags: report.feature_flags,
                configured_fields_scanned_across_tabs: report.visible_fields_scanned
            });
            console.log('Copyable debug report:');
            console.log(JSON.stringify(report, null, 2));
            console.table(report.fields);
            if (report.matches.length) {
                console.info('TRANSCRIPT ACTIONS ADDED:', report.matches.length, 'matching field(s).');
                console.table(report.matches);
            } else {
                console.warn('NO CONVERSION BUTTONS ADDED. Check fields[].preview, tab_name, enabled_for_transcript_detection, and should_show_convert_action.');
            }
            console.groupEnd();
        }
    }

    // Helper function to copy transcript value
    function copyTranscriptValue(elementId) {
        var data = window._transcriptData[elementId];
        if (data) {
            copyToClipboard(data.value);
        } else {
            showDialog('Info', 'No transcript data to copy.');
        }
    }

    // Function to detect character data from other elements
    function detectCharacterData() {
        var addEntryTab = document.getElementById('user_tab_add_entry');
        if (!addEntryTab) return;
        
        var activeContent = addEntryTab.querySelector('.dynamic-sub-tab-content.active');
        if (!activeContent) return;
        
        var elements = activeContent.querySelectorAll('input, textarea, select');
        
        var foundCharacterData = null;
        
        elements.forEach(function(element) {
            var value = element.value || element.textContent || '';
            if (!value) return;
            
            // Look for JSON character data
            var charData = extractCharacterDataFromString(value);
            if (charData && Object.keys(charData).length > 0) {
                foundCharacterData = charData;
                console.log('✅ Found character data in element:', element.id || 'unnamed');
            }
        });
        
        // If found character data, store it globally
        if (foundCharacterData) {
            window._characterData = foundCharacterData;
            console.log('✅ Character data stored globally with ' + Object.keys(foundCharacterData).length + ' characters');
        }
    }

    // Extract character data from a string
    function extractCharacterDataFromString(text) {
        var characterData = {};
        
        if (!text) return characterData;
        
        // Look for JSON array format: [{"character": "Name", ...}, ...]
        var jsonArrayMatch = text.match(/\[\s*\{[^}]*"character"\s*:\s*"[^"]*"[^}]*\}\s*(?:,\s*\{[^}]*"character"\s*:\s*"[^"]*"[^}]*\}\s*)*\]/);
        if (jsonArrayMatch) {
            try {
                var charArray = JSON.parse(jsonArrayMatch[0]);
                if (Array.isArray(charArray)) {
                    charArray.forEach(function(charObj) {
                        var characterName = charObj.character || '';
                        if (characterName) {
                            var relation = charObj.relation || '';
                            var castDetails = charObj.character_details || '';
                            var prompt = charObj.character_visual_prompt || '';
                            
                            // Extract clean name from character field (remove parentheses, special chars)
                            var cleanName = extractCleanName(characterName);
                            
                            var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                            
                            characterData[characterName] = {
                                name: characterName,
                                clean_name: cleanName,
                                relation: relation,
                                character_details: castDetails,
                                details: fullDetails,
                                prompt: prompt,
                                // Store all possible variations for matching
                                variations: generateNameVariations(cleanName, characterName)
                            };
                        }
                    });
                    if (Object.keys(characterData).length > 0) {
                        return characterData;
                    }
                }
            } catch (e) {
                console.log('⚠️ Failed to parse JSON array:', e.message);
            }
        }
        
        // Look for individual character objects
        var charObjects = text.match(/\{[^}]*"character"\s*:\s*"[^"]*"[^}]*"relation"\s*:\s*"[^"]*"[^}]*"character_details"\s*:\s*"[^"]*"[^}]*"character_visual_prompt"\s*:\s*"[^"]*"[^}]*\}/g);
        if (charObjects) {
            charObjects.forEach(function(charObjStr) {
                try {
                    var charObj = JSON.parse(charObjStr);
                    var characterName = charObj.character || '';
                    if (characterName) {
                        var relation = charObj.relation || '';
                        var castDetails = charObj.character_details || '';
                        var prompt = charObj.character_visual_prompt || '';
                        
                        var cleanName = extractCleanName(characterName);
                        
                        var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                        
                        characterData[characterName] = {
                            name: characterName,
                            clean_name: cleanName,
                            relation: relation,
                            character_details: castDetails,
                            details: fullDetails,
                            prompt: prompt,
                            variations: generateNameVariations(cleanName, characterName)
                        };
                    }
                } catch (e) {
                    // Skip invalid JSON objects
                }
            });
            if (Object.keys(characterData).length > 0) {
                return characterData;
            }
        }
        
        // Look for JSON code block
        var jsonCodeMatch = text.match(/```json\s*(\[[\s\S]*?\])\s*```/);
        if (jsonCodeMatch) {
            try {
                var charArray2 = JSON.parse(jsonCodeMatch[1]);
                if (Array.isArray(charArray2)) {
                    charArray2.forEach(function(charObj) {
                        var characterName = charObj.character || '';
                        if (characterName) {
                            var relation = charObj.relation || '';
                            var castDetails = charObj.character_details || '';
                            var prompt = charObj.character_visual_prompt || '';
                            
                            var cleanName = extractCleanName(characterName);
                            
                            var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                            
                            characterData[characterName] = {
                                name: characterName,
                                clean_name: cleanName,
                                relation: relation,
                                character_details: castDetails,
                                details: fullDetails,
                                prompt: prompt,
                                variations: generateNameVariations(cleanName, characterName)
                            };
                        }
                    });
                    if (Object.keys(characterData).length > 0) {
                        return characterData;
                    }
                }
            } catch (e) {
                console.log('⚠️ Failed to parse JSON code block:', e.message);
            }
        }
        
        return characterData;
    }

    // Extract clean name from character field (remove parentheses and special chars)
    function extractCleanName(characterName) {
        // Remove anything in parentheses
        var cleanName = characterName.replace(/\([^)]*\)/g, '').trim();
        // Remove extra spaces
        cleanName = cleanName.replace(/\s+/g, ' ').trim();
        // If cleanName is empty, use the original
        if (!cleanName) cleanName = characterName;
        return cleanName;
    }

    // Generate variations of a name for intelligent matching
    function generateNameVariations(cleanName, fullName) {
        var variations = new Set();
        
        // Add clean name
        if (cleanName) {
            variations.add(cleanName.toLowerCase());
            // Add without spaces
            variations.add(cleanName.toLowerCase().replace(/\s+/g, ''));
        }
        
        // Add full name variations
        if (fullName) {
            var fullLower = fullName.toLowerCase();
            variations.add(fullLower);
            // Remove parentheses and commas
            var stripped = fullLower.replace(/[(),]/g, '').replace(/\s+/g, ' ').trim();
            variations.add(stripped);
            variations.add(stripped.replace(/\s+/g, ''));
        }
        
        // Split by commas, spaces, and extract individual words
        var parts = fullName.split(/[,\s]+/);
        parts.forEach(function(part) {
            part = part.trim().toLowerCase();
            if (part.length > 2) { // Only consider meaningful words
                variations.add(part);
                // Remove parentheses from part
                var cleanPart = part.replace(/[()]/g, '').trim();
                if (cleanPart.length > 2) {
                    variations.add(cleanPart);
                }
            }
        });
        
        // Generate combinations of words (2-word, 3-word combos)
        var words = [];
        parts.forEach(function(part) {
            part = part.trim().toLowerCase().replace(/[()]/g, '');
            if (part.length > 2) {
                words.push(part);
            }
        });
        
        // Generate 2-word combinations
        for (var i = 0; i < words.length; i++) {
            for (var j = i + 1; j < words.length; j++) {
                var combo = words[i] + words[j];
                variations.add(combo);
                var comboSpace = words[i] + ' ' + words[j];
                variations.add(comboSpace);
            }
        }
        
        // Generate 3-word combinations
        for (var i = 0; i < words.length; i++) {
            for (var j = i + 1; j < words.length; j++) {
                for (var k = j + 1; k < words.length; k++) {
                    var combo = words[i] + words[j] + words[k];
                    variations.add(combo);
                    var comboSpace = words[i] + ' ' + words[j] + ' ' + words[k];
                    variations.add(comboSpace);
                }
            }
        }
        
        // Return as array
        return Array.from(variations);
    }

    // Function to open transcript dialog
    function openTranscriptDialog(elementId) {
        // Validate against the tab that owns this transcript field, not whichever
        // tab happens to be active when the dialog is opened.
        var data = window._transcriptData && window._transcriptData[elementId];
        var features = data && data.features ? data.features : getActiveTabFeatures();
        if (!sceneIQFeatureEnabled(features.transcript_detection)) {
            console.warn('[SceneIQ Transcript Detection] View Transcript blocked: transcript_detection is disabled for the owning tab.', features);
            showDialog('Info', 'Transcript detection is not enabled for this tab. Enable it in the server-side tab configuration and save.');
            return;
        }

        if (!data) {
            showDialog('Error', 'Transcript data not found.');
            return;
        }
        
        var characterStatus = window._characterData ? 
            '<span style="color:#065f46;">✅ Character data found (' + Object.keys(window._characterData).length + ' characters)</span>' : 
            '<span style="color:#f59e0b;">⚠️ No character data found - converting transcript only</span>';
        
        var content = 
            '<div style="margin-bottom:15px;">' +
            '<label style="display:block; font-weight:600; color:#1a1a2e; margin-bottom:8px;">Transcript Content</label>' +
            '<textarea id="transcriptTextarea" rows="12" style="width:100%; padding:12px; border:2px solid #e5e7eb; border-radius:8px; font-family:monospace; font-size:14px; background:#fafafa; resize:vertical;">' + 
            data.value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + 
            '</textarea>' +
            '</div>' +
            '<div style="margin-bottom:15px; padding:10px; background:#f8fafc; border-radius:8px; border:1px solid #e5e7eb;">' +
            '<div style="font-size:13px; color:#1a1a2e;">' + characterStatus + '</div>' +
            '</div>' +
            '<div style="margin-top:10px;">' +
            '<button type="button" class="btn btn-primary" onclick="convertTranscriptToJson(\'' + elementId + '\')" style="width:100%; padding:12px;">🔄 Convert Transcript to JSON</button>' +
            '</div>' +
            '<div id="transcriptConversionResult" style="margin-top:15px; display:none;"></div>' +
            '<div id="transcriptJsonResult" style="margin-top:15px; display:none;"></div>';
        
        showDialog('Transcript Viewer', '', null, content);
    }

    // NEW FUNCTION: Convert to Text format with batches
    function convertToText(elementId) {
        // Check if structured data detection is enabled for this tab
        var features = getActiveTabFeatures();
        if (features.transcript_with_structured_data_detection !== true) {
            showDialog('Info', 'Structured data detection is not enabled for this tab.');
            return;
        }
        
        var data = window._transcriptData[elementId];
        if (!data) {
            showDialog('Error', 'Transcript data not found.');
            return;
        }
        
        var transcriptText = data.value;
        if (!transcriptText || transcriptText.trim() === '') {
            showDialog('Error', 'Transcript is empty.');
            return;
        }
        
        // Show loading indicator
        var indicator = document.getElementById('transcript_indicator_' + elementId);
        if (indicator) {
            var convertBtn = indicator.querySelector('.btn-primary');
            if (convertBtn && convertBtn.textContent.includes('Convert to Text')) {
                convertBtn.textContent = '⏳ Processing...';
                convertBtn.disabled = true;
            }
        }
        
        setTimeout(function() {
            try {
                var result = processStructuredTextConversion(transcriptText);
                
                // Store result
                window._conversionResults[elementId + '_text'] = result;
                
                // Remove any existing result div first
                var existingResultDiv = document.getElementById('transcript_result_' + elementId);
                if (existingResultDiv) {
                    existingResultDiv.remove();
                }
                
                // Create result display
                var resultDiv = document.createElement('div');
                resultDiv.id = 'transcript_result_' + elementId;
                resultDiv.style.cssText = 'margin-top:8px; padding:12px; background:#f0fdf4; border-radius:8px; border:1px solid #a7f3d0;';
                
                resultDiv.innerHTML = 
                    '<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:10px;">' +
                    '<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">' +
                    '<span style="color:#065f46; font-weight:600;">✅ Text Conversion Complete</span>' +
                    '<span style="font-size:12px; color:#065f46; background:#d1fae5; padding:2px 8px; border-radius:12px;">📊 ' + result.totalEntries + ' entries</span>' +
                    '<span style="font-size:12px; color:#065f46; background:#d1fae5; padding:2px 8px; border-radius:12px;">📦 ' + result.batches + ' batches</span>' +
                    '</div>' +
                    '<div style="display:flex; gap:6px; flex-wrap:wrap;">' +
                    '<button type="button" class="btn btn-primary btn-sm" onclick="copyTextResult(\'' + elementId + '\')" style="padding:2px 10px; font-size:11px;">📋 Copy Text</button>' +
                    '<button type="button" class="btn btn-sm" onclick="toggleInlineResult(\'' + elementId + '\')" style="padding:2px 10px; font-size:11px; background:#e5e7eb; color:#374151;">✕</button>' +
                    '</div>' +
                    '</div>' +
                    '<div style="background:#1a1a2e; color:#e5e7eb; padding:12px; border-radius:6px; overflow:auto; max-height:400px; font-size:12px; font-family:monospace; white-space:pre-wrap; word-break:break-word;">' + 
                    result.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + 
                    '</div>';
                
                // Insert after indicator
                var indicatorEl = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl) {
                    indicatorEl.parentNode.insertBefore(resultDiv, indicatorEl.nextSibling);
                }
                
                // Reset button
                if (indicatorEl) {
                    var convertBtn2 = indicatorEl.querySelector('.btn-primary');
                    if (convertBtn2 && convertBtn2.textContent.includes('Convert to Text')) {
                        convertBtn2.textContent = '📄 Convert to Text';
                        convertBtn2.disabled = false;
                    }
                }
                
            } catch (error) {
                // Reset button
                var indicatorEl2 = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl2) {
                    var convertBtn3 = indicatorEl2.querySelector('.btn-primary');
                    if (convertBtn3 && convertBtn3.textContent.includes('Convert to Text')) {
                        convertBtn3.textContent = '📄 Convert to Text';
                        convertBtn3.disabled = false;
                    }
                }
                
                // Show error
                var errorDiv = document.createElement('div');
                errorDiv.id = 'transcript_result_' + elementId;
                errorDiv.style.cssText = 'margin-top:8px; padding:10px; background:#fef2f2; border-radius:8px; border:1px solid #fecaca; color:#dc2626;';
                errorDiv.textContent = '❌ Error: ' + error.message;
                
                var indicatorEl3 = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl3) {
                    indicatorEl3.parentNode.insertBefore(errorDiv, indicatorEl3.nextSibling);
                }
            }
        }, 100);
    }

    // Copy text result
    function copyTextResult(elementId) {
        var result = window._conversionResults[elementId + '_text'];
        if (!result) {
            showDialog('Error', 'No conversion result found.');
            return;
        }
        copyToClipboard(result.text);
    }

    // Find characters mentioned in a text (scene_Image_generation or dialogue)
    function findMentionedCharacters(text, characterPrompts) {
        var mentioned = [];
        if (!text || !characterPrompts) return mentioned;
        
        var textUpper = text.toUpperCase();
        
        for (var key in characterPrompts) {
            if (characterPrompts.hasOwnProperty(key)) {
                var keyUpper = key.toUpperCase();
                // Check if character name appears in the text
                if (textUpper.includes(keyUpper)) {
                    mentioned.push(key);
                }
                // Also check for variations
                var charInfo = characterPrompts[key];
                if (charInfo.clean_name) {
                    var cleanUpper = charInfo.clean_name.toUpperCase();
                    if (cleanUpper !== keyUpper && textUpper.includes(cleanUpper)) {
                        if (mentioned.indexOf(key) === -1) {
                            mentioned.push(key);
                        }
                    }
                }
            }
        }
        
        return mentioned;
    }

    // Process structured text conversion - handles both array and batch formats
    function processStructuredTextConversion(transcriptText) {
        // Parse the full JSON from the text
        var parsedData = null;
        try {
            var startIdx = transcriptText.indexOf('{');
            if (startIdx === -1) {
                throw new Error('No JSON object found in text');
            }
            
            var braceCount = 0;
            var endIdx = -1;
            for (var i = startIdx; i < transcriptText.length; i++) {
                if (transcriptText[i] === '{') braceCount++;
                else if (transcriptText[i] === '}') {
                    braceCount--;
                    if (braceCount === 0) {
                        endIdx = i + 1;
                        break;
                    }
                }
            }
            
            if (endIdx === -1) {
                throw new Error('Could not find matching closing brace for JSON object');
            }
            
            var jsonStr = transcriptText.substring(startIdx, endIdx);
            parsedData = JSON.parse(jsonStr);
        } catch (e) {
            console.log('⚠️ Failed to parse JSON:', e.message);
            throw new Error('Failed to parse structured JSON data: ' + e.message);
        }
        
        if (!parsedData || !parsedData.script) {
            throw new Error('Invalid structured data: missing script');
        }
        
        var scriptEntries = [];
        
        // Check if script is an array or object with batches
        if (Array.isArray(parsedData.script)) {
            // Array format - use as is
            scriptEntries = parsedData.script;
        } else if (typeof parsedData.script === 'object') {
            // Batch format - extract entries from all batches
            for (var batchKey in parsedData.script) {
                if (parsedData.script.hasOwnProperty(batchKey)) {
                    var batch = parsedData.script[batchKey];
                    if (batch && batch.entries && Array.isArray(batch.entries)) {
                        scriptEntries = scriptEntries.concat(batch.entries);
                    }
                }
            }
        }
        
        if (scriptEntries.length === 0) {
            throw new Error('No script entries found');
        }
        
        // Process all entries WITHOUT distributing characters to view_focus_characters
        var updatedScriptEntries = [];
        var charPrompts = parsedData.characters_visual_prompts || {};
        
        for (var idx = 0; idx < scriptEntries.length; idx++) {
            var entry = scriptEntries[idx];
            
            // Extract view_focus_characters - if it exists, use it, otherwise extract from view_focus
            var viewFocusChars = '';
            if (entry.view_focus_characters) {
                viewFocusChars = entry.view_focus_characters;
            } else if (entry.view_focus) {
                // Try to extract from view_focus
                viewFocusChars = entry.view_focus;
            }
            
            // Parse view focus characters - handle "and" and commas
            var charNames = [];
            if (viewFocusChars) {
                // Split by "and" or commas
                var parts = viewFocusChars.split(/\s+and\s+|\s*,\s*/);
                parts.forEach(function(part) {
                    var trimmed = part.trim();
                    if (trimmed) {
                        charNames.push(trimmed);
                    }
                });
            }
            
            // Also check for characters in scene_Image_generation and dialogue
            var scenePov = entry.scene_Image_generation || entry.scene_Image_generation || '';
            var dialogue = entry.dialogue || '';
            var allText = scenePov + ' ' + dialogue;
            
            // Find mentioned characters
            var mentionedChars = findMentionedCharacters(allText, charPrompts);
            
            // Combine with view focus characters
            var allCharNames = charNames.slice();
            mentionedChars.forEach(function(charName) {
                if (allCharNames.indexOf(charName) === -1) {
                    allCharNames.push(charName);
                }
            });
            
            // Create updated entry WITHOUT view_focus_characters distribution
            var updatedEntry = {
                start: entry.start || '',
                stop: entry.stop || '',
                duration: entry.duration || '',
                view_focus_characters: '', // Always empty - no distribution
                dialogue: entry.dialogue || '',
                scene_Image_generation: entry.scene_Image_generation || entry.scene_Image_generation || '',
                // Store character names for details display
                _characters: allCharNames
            };
            
            updatedScriptEntries.push(updatedEntry);
        }
        
        // Generate text output with batches of 20
        var textOutput = 'SCENES DIALOGUE\n\n';
        var batchSize = 20;
        var totalEntries = updatedScriptEntries.length;
        var totalBatches = Math.ceil(totalEntries / batchSize);
        
        for (var b = 0; b < totalBatches; b++) {
            var startIdx2 = b * batchSize;
            var endIdx2 = Math.min((b + 1) * batchSize, totalEntries);
            var batchStart = startIdx2 + 1;
            var batchEnd = endIdx2;
            
            textOutput += 'BATCH ' + batchStart + ' - ' + batchEnd + '\n\n';
            
            for (var j = startIdx2; j < endIdx2; j++) {
                var entry = updatedScriptEntries[j];
                var entryNum = j + 1;
                
                textOutput += entryNum + '.\n';
                
                // Add View Focus Characters
                if (entry._characters && entry._characters.length > 0) {
                    textOutput += 'View Focus Characters: ' + entry._characters.join(' and ') + '\n';
                } else {
                    textOutput += 'View Focus Characters: (none)\n';
                }
                
                // Add character details for each character
                if (entry._characters && entry._characters.length > 0) {
                    for (var c = 0; c < entry._characters.length; c++) {
                        var charName = entry._characters[c];
                        var charInfo = charPrompts[charName];
                        if (charInfo) {
                            textOutput += charName + ' Details:\n';
                            textOutput += '    relation: ' + (charInfo.relation || '') + '\n';
                            textOutput += '    details: ' + (charInfo.character_details || '') + '\n';
                        }
                    }
                }
                
                textOutput += 'Dialogue: ' + (entry.dialogue || '') + '\n';
                textOutput += 'Scene Pov Promt: ' + (entry.scene_Image_generation || '') + '\n\n';
            }
        }
        
        return {
            text: textOutput,
            totalEntries: totalEntries,
            batches: totalBatches,
            script: updatedScriptEntries
        };
    }

    // NEW FUNCTION: Convert and display inline without modal
    function convertAndDisplayInline(elementId) {
        // Validate against the feature flags captured for this field during scanning.
        var data = window._transcriptData && window._transcriptData[elementId];
        var features = data && data.features ? data.features : getActiveTabFeatures();
        console.info('[SceneIQ Transcript Detection] CONVERT TO JSON CLICKED', {
            element_id: elementId,
            owning_tab: data && data.tabDetails ? data.tabDetails.root_name : null,
            owning_child_tab: data && data.tabDetails ? data.tabDetails.child_name : null,
            feature_flags: features,
            transcript_detection_enabled: sceneIQFeatureEnabled(features.transcript_detection),
            transcript_payload_available: !!data
        });
        if (!sceneIQFeatureEnabled(features.transcript_detection)) {
            console.warn('[SceneIQ Transcript Detection] Convert to JSON blocked: transcript_detection is disabled for the owning tab.', features);
            showDialog('Info', 'Transcript detection is not enabled for this tab. Enable it in the server-side tab configuration and save.');
            return;
        }

        if (!data) {
            showDialog('Error', 'Transcript data not found.');
            return;
        }
        
        var transcriptText = data.value;
        if (!transcriptText || transcriptText.trim() === '') {
            showDialog('Error', 'Transcript is empty.');
            return;
        }
        
        // Check if result already exists
        var existingResult = document.getElementById('transcript_result_' + elementId);
        if (existingResult) {
            // If exists, just toggle visibility or refresh
            if (existingResult.style.display === 'none') {
                existingResult.style.display = 'block';
            } else {
                // Re-convert
                existingResult.remove();
                delete window._conversionResults[elementId];
            }
        }
        
        // Show loading indicator
        var indicator = document.getElementById('transcript_indicator_' + elementId);
        if (indicator) {
            var convertBtn = indicator.querySelector('.btn-success');
            if (convertBtn) {
                convertBtn.textContent = '⏳ Processing...';
                convertBtn.disabled = true;
            }
        }
        
        setTimeout(function() {
            try {
                var characterData = window._characterData || null;
                var result = processTranscriptConversion(transcriptText, characterData);
                
                // Store result
                window._conversionResults[elementId] = result;
                
                // Remove any existing result div first
                var existingResultDiv = document.getElementById('transcript_result_' + elementId);
                if (existingResultDiv) {
                    existingResultDiv.remove();
                }
                
                // Create result display
                var resultDiv = document.createElement('div');
                resultDiv.id = 'transcript_result_' + elementId;
                resultDiv.style.cssText = 'margin-top:8px; padding:12px; background:#f0fdf4; border-radius:8px; border:1px solid #a7f3d0;';
                
                // Build character status
                var charStatus = characterData && Object.keys(characterData).length > 0 ? 
                    '👤 ' + Object.keys(characterData).length + ' characters' : 
                    '👤 No character data';
                
                resultDiv.innerHTML = 
                    '<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:10px;">' +
                    '<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">' +
                    '<span style="color:#065f46; font-weight:600;">✅ Conversion Complete</span>' +
                    '<span style="font-size:12px; color:#065f46; background:#d1fae5; padding:2px 8px; border-radius:12px;">📊 ' + result.script.length + ' entries</span>' +
                    '<span style="font-size:12px; color:#065f46; background:#d1fae5; padding:2px 8px; border-radius:12px;">' + charStatus + '</span>' +
                    '</div>' +
                    '<div style="display:flex; gap:6px; flex-wrap:wrap;">' +
                    '<button type="button" class="btn btn-primary btn-sm" onclick="copyInlineJson(\'' + elementId + '\')" style="padding:2px 10px; font-size:11px;">📋 Copy JSON</button>' +
                    '<button type="button" class="btn btn-sm" onclick="toggleInlineResult(\'' + elementId + '\')" style="padding:2px 10px; font-size:11px; background:#e5e7eb; color:#374151;">✕</button>' +
                    '</div>' +
                    '</div>' +
                    '<div style="background:#1a1a2e; color:#e5e7eb; padding:12px; border-radius:6px; overflow:auto; max-height:250px; font-size:11px; font-family:monospace; white-space:pre-wrap; word-break:break-all;">' + 
                    result.jsonString.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + 
                    '</div>';
                
                // Insert after indicator
                var indicatorEl = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl) {
                    indicatorEl.parentNode.insertBefore(resultDiv, indicatorEl.nextSibling);
                } else {
                    // Fallback: find container
                    var container = document.querySelector('.form-group') || document.body;
                    container.appendChild(resultDiv);
                }
                
                // Reset button
                if (indicatorEl) {
                    var convertBtn2 = indicatorEl.querySelector('.btn-success');
                    if (convertBtn2) {
                        convertBtn2.textContent = '🔄 Convert to JSON';
                        convertBtn2.disabled = false;
                    }
                }
                
            } catch (error) {
                // Reset button
                var indicatorEl2 = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl2) {
                    var convertBtn3 = indicatorEl2.querySelector('.btn-success');
                    if (convertBtn3) {
                        convertBtn3.textContent = '🔄 Convert to JSON';
                        convertBtn3.disabled = false;
                    }
                }
                
                // Show error
                var errorDiv = document.createElement('div');
                errorDiv.id = 'transcript_result_' + elementId;
                errorDiv.style.cssText = 'margin-top:8px; padding:10px; background:#fef2f2; border-radius:8px; border:1px solid #fecaca; color:#dc2626;';
                errorDiv.textContent = '❌ Error: ' + error.message;
                
                var indicatorEl3 = document.getElementById('transcript_indicator_' + elementId);
                if (indicatorEl3) {
                    indicatorEl3.parentNode.insertBefore(errorDiv, indicatorEl3.nextSibling);
                }
            }
        }, 100);
    }

    // Toggle inline result visibility
    function toggleInlineResult(elementId) {
        var resultDiv = document.getElementById('transcript_result_' + elementId);
        if (resultDiv) {
            if (resultDiv.style.display === 'none') {
                resultDiv.style.display = 'block';
            } else {
                resultDiv.style.display = 'none';
            }
        }
    }

    // Copy inline JSON result
    function copyInlineJson(elementId) {
        var result = window._conversionResults[elementId];
        if (!result) {
            showDialog('Error', 'No conversion result found.');
            return;
        }
        copyToClipboard(result.jsonString);
    }

    // Download inline JSON result
    function downloadInlineJson(elementId) {
        var result = window._conversionResults[elementId];
        if (!result) {
            showDialog('Error', 'No conversion result found.');
            return;
        }
        var blob = new Blob([result.jsonString], {type: 'application/json'});
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'transcript_converted.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Function to convert transcript to JSON (for modal)
    function convertTranscriptToJson(elementId) {
        var textarea = document.getElementById('transcriptTextarea');
        if (!textarea) {
            showDialog('Error', 'Transcript content not found.');
            return;
        }
        
        var transcriptText = textarea.value;
        if (!transcriptText || transcriptText.trim() === '') {
            showDialog('Error', 'Transcript is empty.');
            return;
        }
        
        var resultDiv = document.getElementById('transcriptConversionResult');
        if (resultDiv) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div style="color:#00695c; padding:10px; text-align:center;">⏳ Processing transcript...</div>';
        }
        
        setTimeout(function() {
            try {
                var characterData = window._characterData || null;
                var result = processTranscriptConversion(transcriptText, characterData);
                
                // Build detailed log message
                var logMessages = [];
                logMessages.push('📁 [CONVERT] Processing transcript...');
                logMessages.push('📖 [CONVERT] Reading transcript content...');
                logMessages.push('✅ [CONVERT] Found ' + result.timestamps + ' timestamps');
                
                if (characterData && Object.keys(characterData).length > 0) {
                    var charNames = Object.keys(characterData);
                    logMessages.push('📋 [CONVERT] Found character data: ' + JSON.stringify(charNames));
                    logMessages.push('✅ [CONVERT] Extracted ' + charNames.length + ' characters from character data');
                    logMessages.push('📋 [CONVERT] Character data extracted: ' + JSON.stringify(charNames));
                    // Log variations for each character
                    for (var charName in characterData) {
                        if (characterData[charName].variations) {
                            logMessages.push('🔍 [CONVERT] "' + charName + '" variations: ' + JSON.stringify(characterData[charName].variations));
                        }
                    }
                } else {
                    logMessages.push('⚠️ [CONVERT] No character data found, proceeding without character prompts');
                }
                
                logMessages.push('✅ [CONVERT] Parsed ' + result.script.length + ' dialogue entries');
                logMessages.push('✅ [CONVERT] JSON conversion complete');
                logMessages.push('📊 [CONVERT] Total dialogue entries: ' + result.script.length);
                
                var logHtml = logMessages.map(function(msg) {
                    var color = '#6b7280';
                    if (msg.indexOf('✅') !== -1) color = '#065f46';
                    else if (msg.indexOf('📋') !== -1) color = '#00695c';
                    else if (msg.indexOf('⚠️') !== -1) color = '#f59e0b';
                    else if (msg.indexOf('❌') !== -1) color = '#ef4444';
                    else if (msg.indexOf('🔍') !== -1) color = '#8b5cf6';
                    else if (msg.indexOf('📁') !== -1 || msg.indexOf('📖') !== -1) color = '#2563eb';
                    else if (msg.indexOf('📊') !== -1) color = '#7c3aed';
                    return '<div style="color:' + color + '; font-family:monospace; font-size:13px; padding:2px 0;">' + msg + '</div>';
                }).join('');
                
                var jsonResultDiv = document.getElementById('transcriptJsonResult');
                if (jsonResultDiv) {
                    jsonResultDiv.style.display = 'block';
                    jsonResultDiv.innerHTML = 
                        '<div style="background:#f0fdf4; border-radius:8px; padding:15px; border:1px solid #a7f3d0;">' +
                        '<div style="color:#065f46; font-weight:600; margin-bottom:8px;">✅ Conversion Complete</div>' +
                        '<div style="font-size:13px; color:#065f46; margin-bottom:10px;">' +
                        '📊 ' + result.script.length + ' dialogue entries parsed' +
                        (characterData && Object.keys(characterData).length > 0 ? ' | 👤 ' + Object.keys(characterData).length + ' characters extracted' : ' | 👤 No character data') +
                        '</div>' +
                        '<div style="background:#f8fafc; border-radius:8px; padding:12px; margin-bottom:10px; border:1px solid #e5e7eb; max-height:200px; overflow-y:auto;">' +
                        logHtml +
                        '</div>' +
                        '<div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">' +
                        '<button type="button" class="btn btn-primary btn-sm" onclick="copyJsonResult()">📋 Copy JSON</button>' +
                        '</div>' +
                        '<pre style="background:#1a1a2e; color:#e5e7eb; padding:15px; border-radius:8px; overflow:auto; max-height:300px; font-size:12px; white-space:pre-wrap; word-break:break-all; margin-top:10px;">' + 
                        result.jsonString.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + 
                        '</pre>' +
                        '</div>';
                }
                
                if (resultDiv) {
                    resultDiv.style.display = 'none';
                }
                
                window._transcriptResult = result;
                
            } catch (error) {
                if (resultDiv) {
                    resultDiv.innerHTML = '<div style="color:#ef4444; padding:10px; text-align:center;">❌ Error: ' + error.message + '</div>';
                }
            }
        }, 100);
    }

    // Normalize transcript text - remove special characters around timestamps
    function normalizeTranscriptText(text) {
        var normalized = text;
        var jsonArrayMatch = text.match(/^[\s\n\r]*\[\s*\{[^]*\}\s*\]\s*/);
        if (jsonArrayMatch) {
            normalized = text.substring(jsonArrayMatch[0].length);
        }
        normalized = normalized.replace(/[\(\[\{\-\_\s]*(\d{1,2}:\d{2})[\)\]\}\-\_\s]*/g, '$1');
        normalized = normalized.replace(/^[\(\[\{\-\_\s]*(\d{1,2}:\d{2})[\)\]\}\-\_\s]*/gm, '$1');
        normalized = normalized.replace(/(\d{1,2}:\d{2})[\)\]\}\-\_]/g, '$1');
        normalized = normalized.replace(/[\(\[\{\-\_]( \d{1,2}:\d{2})/g, '$1');
        return normalized;
    }

    // Main conversion engine - WITHOUT view_focus_characters and WITHOUT remaining_nonfeatured_characters
    function processTranscriptConversion(transcriptText, characterData) {
        // ===== Extract character data from JSON array at the beginning if not provided =====
        if (!characterData || Object.keys(characterData).length === 0) {
            characterData = extractCharacterDataFromJson(transcriptText);
        }
        
        // ===== Extract only the transcript part (remove JSON) =====
        var transcriptOnly = extractTranscriptOnly(transcriptText);
        
        // ===== Parse the transcript - find all timestamps =====
        var normalizedText = normalizeTranscriptText(transcriptOnly);
        var timestampPattern = /(\d{1,2}:\d{2})/g;
        var matches = [];
        var match;
        
        while ((match = timestampPattern.exec(normalizedText)) !== null) {
            var timeParts = match[1].split(':');
            var minutes = parseInt(timeParts[0]);
            var seconds = parseInt(timeParts[1]);
            var timeStr = minutes + ':' + String(seconds).padStart(2, '0');
            var timeSeconds = minutes * 60 + seconds;
            matches.push({
                time_str: timeStr,
                time_seconds: timeSeconds,
                start_pos: match.index,
                end_pos: match.index + match[0].length
            });
        }
        
        if (matches.length === 0) {
            throw new Error('No timestamps found in transcript');
        }
        
        // ===== Build script entries WITHOUT view_focus_characters =====
        var scriptLines = [];
        
        // Include every timestamp, including the final timestamp. Preserve all trailing text.
        for (var i = 0; i < matches.length; i++) {
            var current = matches[i];
            var nextMatch = (i + 1 < matches.length) ? matches[i + 1] : null;
            var dialogueStart = current.end_pos;
            var dialogueEnd = nextMatch ? nextMatch.start_pos : normalizedText.length;
            var dialogueText = normalizedText.substring(dialogueStart, dialogueEnd).trim();
            dialogueText = dialogueText.replace(/\d{1,2}:\d{2}/g, '').replace(/\s+/g, ' ').trim();

            if (dialogueText) {
                var scriptEntry = {
                    start: current.time_str,
                    stop: nextMatch ? nextMatch.time_str : 'the end',
                    duration: nextMatch ? (nextMatch.time_seconds - current.time_seconds) + ' seconds' : 'until the end',
                    view_focus_characters: '',
                    dialogue: dialogueText,
                    scene_Image_generation: ''
                };
                scriptLines.push(scriptEntry);
            }
        }

        if (scriptLines.length === 0) {
            throw new Error('No dialogue entries could be parsed');
        }
        
        // ===== Create JSON output containing only script =====
        // characters_visual_prompts is intentionally omitted from conversion output.
        var jsonData = {
            script: scriptLines
        };
        
        return {
            script: scriptLines,
            characters: characterData,
            remaining: {}, // Always empty
            timestamps: matches.length,
            json: jsonData,
            jsonString: JSON.stringify(jsonData, null, 4)
        };
    }

    // Extract character data from JSON array at the beginning (kept for backward compatibility)
    function extractCharacterDataFromJson(transcriptText) {
        var characterData = {};
        
        // Look for the JSON array format: [{"character": "Name", ...}, ...]
        var jsonPattern = /\[\s*\{[^}]*"character"\s*:\s*"[^"]*"[^}]*\}\s*(?:,\s*\{[^}]*"character"\s*:\s*"[^"]*"[^}]*\}\s*)*\]/;
        var jsonMatch = transcriptText.match(jsonPattern);
        
        if (jsonMatch) {
            try {
                var jsonStr = jsonMatch[0];
                var characterArray = JSON.parse(jsonStr);
                
                if (Array.isArray(characterArray)) {
                    characterArray.forEach(function(charObj) {
                        var characterName = charObj.character || '';
                        if (characterName) {
                            var relation = charObj.relation || '';
                            var castDetails = charObj.character_details || '';
                            var prompt = charObj.character_visual_prompt || '';
                            
                            var cleanName = extractCleanName(characterName);
                            
                            var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                            
                            characterData[characterName] = {
                                name: characterName,
                                clean_name: cleanName,
                                relation: relation,
                                character_details: castDetails,
                                details: fullDetails,
                                prompt: prompt,
                                variations: generateNameVariations(cleanName, characterName)
                            };
                        }
                    });
                    
                    if (Object.keys(characterData).length > 0) {
                        console.log('✅ [CONVERT] Extracted ' + Object.keys(characterData).length + ' characters from JSON array');
                        return characterData;
                    }
                }
            } catch (e) {
                console.log('⚠️ [CONVERT] Failed to parse JSON array:', e.message);
            }
        }
        
        // Method 2: Try to find individual character objects
        var charObjects = transcriptText.match(/\{[^}]*"character"\s*:\s*"[^"]*"[^}]*"relation"\s*:\s*"[^"]*"[^}]*"character_details"\s*:\s*"[^"]*"[^}]*"character_visual_prompt"\s*:\s*"[^"]*"[^}]*\}/g);
        
        if (charObjects) {
            charObjects.forEach(function(charObjStr) {
                try {
                    var charObj = JSON.parse(charObjStr);
                    var characterName = charObj.character || '';
                    if (characterName) {
                        var relation = charObj.relation || '';
                        var castDetails = charObj.character_details || '';
                        var prompt = charObj.character_visual_prompt || '';
                        
                        var cleanName = extractCleanName(characterName);
                        
                        var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                        
                        characterData[characterName] = {
                            name: characterName,
                            clean_name: cleanName,
                            relation: relation,
                            character_details: castDetails,
                            details: fullDetails,
                            prompt: prompt,
                            variations: generateNameVariations(cleanName, characterName)
                        };
                    }
                } catch (e) {
                    // Skip invalid JSON objects
                }
            });
            
            if (Object.keys(characterData).length > 0) {
                console.log('✅ [CONVERT] Extracted ' + Object.keys(characterData).length + ' characters from individual JSON objects');
                return characterData;
            }
        }
        
        // Method 3: Look for JSON code block
        var jsonCodeMatch = transcriptText.match(/```json\s*(\[[\s\S]*?\])\s*```/);
        if (jsonCodeMatch) {
            try {
                var charArray2 = JSON.parse(jsonCodeMatch[1]);
                if (Array.isArray(charArray2)) {
                    charArray2.forEach(function(charObj) {
                        var characterName = charObj.character || '';
                        if (characterName) {
                            var relation = charObj.relation || '';
                            var castDetails = charObj.character_details || '';
                            var prompt = charObj.character_visual_prompt || '';
                            
                            var cleanName = extractCleanName(characterName);
                            
                            var fullDetails = "**Story Details:**\n" + castDetails + "\n\n**Character Image Generation Prompt:**\n\"" + prompt + "\"";
                            
                            characterData[characterName] = {
                                name: characterName,
                                clean_name: cleanName,
                                relation: relation,
                                character_details: castDetails,
                                details: fullDetails,
                                prompt: prompt,
                                variations: generateNameVariations(cleanName, characterName)
                            };
                        }
                    });
                    
                    if (Object.keys(characterData).length > 0) {
                        console.log('✅ [CONVERT] Extracted ' + Object.keys(characterData).length + ' characters from JSON code block');
                        return characterData;
                    }
                }
            } catch (e) {
                console.log('⚠️ [CONVERT] Failed to parse JSON code block:', e.message);
            }
        }
        
        console.log('⚠️ [CONVERT] No character data found in JSON format');
        return characterData;
    }

    // Extract only the transcript part (remove JSON)
    function extractTranscriptOnly(transcriptText) {
        // Find where the transcript starts - look for the first timestamp
        var timestampPattern = /\(\d{1,2}:\d{2}\)/;
        var firstTimestamp = timestampPattern.exec(transcriptText);
        
        if (firstTimestamp) {
            // Start from the first timestamp
            return transcriptText.substring(firstTimestamp.index);
        }
        
        return transcriptText;
    }

    // Legacy function for backward compatibility
    function findCharactersInDialogue(dialogueText, characterData) {
        return [];
    }

    // Copy JSON result (from modal)
    function copyJsonResult() {
        var result = window._transcriptResult;
        if (!result) {
            showDialog('Error', 'No conversion result found.');
            return;
        }
        copyToClipboard(result.jsonString);
    }

    // Download JSON result (from modal)
    function downloadJsonResult() {
        var result = window._transcriptResult;
        if (!result) {
            showDialog('Error', 'No conversion result found.');
            return;
        }
        var blob = new Blob([result.jsonString], {type: 'application/json'});
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'transcript_converted.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Helper: Copy to clipboard
    function setCopyButtonFeedback(button) {
        if (!button) {
            var active = document.activeElement;
            if (active && active.tagName === 'BUTTON' && /copy/i.test(active.textContent || '')) button = active;
        }
        if (!button || !button.tagName) return;
        if (!button.dataset.originalCopyLabel) button.dataset.originalCopyLabel = button.innerHTML;
        button.innerHTML = '&#10003; Copied';
        button.classList.add('copy-button-copied');
        button.setAttribute('aria-label', 'Copied');
        if (button._copyFeedbackTimer) clearTimeout(button._copyFeedbackTimer);
        button._copyFeedbackTimer = setTimeout(function() {
            button.innerHTML = button.dataset.originalCopyLabel;
            button.classList.remove('copy-button-copied');
            button.removeAttribute('aria-label');
        }, 1800);
    }

    function copyToClipboard(text, button) {
        // Empty strings are valid values too; do not silently skip copying
        // when the current field has intentionally been cleared.
        var textToCopy = typeof text === 'string' ? text : String(text == null ? '' : text);
        if (!button) {
            var active = document.activeElement;
            if (active && active.tagName === 'BUTTON' && /copy/i.test(active.textContent || '')) button = active;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                setCopyButtonFeedback(button);
            }).catch(function() {
                fallbackCopy(textToCopy, button);
            });
        } else {
            fallbackCopy(textToCopy, button);
        }
    }

    function fallbackCopy(text, button) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.pointerEvents = 'none';
        document.body.appendChild(textarea);
        textarea.select();
        var copied = false;
        try { copied = document.execCommand('copy'); } catch (e) { copied = false; }
        document.body.removeChild(textarea);
        if (copied) setCopyButtonFeedback(button);
    }

    // Start transcript detection
    function startTranscriptDetection() {
        detectTranscripts();
        if (window._transcriptDetectionInterval) {
            clearInterval(window._transcriptDetectionInterval);
        }
        window._transcriptDetectionInterval = setInterval(function() {
            detectTranscripts();
        }, 1000);
    }

    // Override switchUserConfigTab to re-detect transcripts when switching to add_entry
    var originalSwitchUserConfigTab = window.switchUserConfigTab || function() {};
    switchUserConfigTab = function(tabName, btn) {
        originalSwitchUserConfigTab(tabName, btn);
        if (tabName === 'add_entry') {
            setTimeout(function() { 
                detectTranscripts();
                updateCopyButtonsVisibility();
            }, 100);
        }
    };

    // Override switchNewProjectSubTab to re-detect transcripts when switching sub-tabs
    var originalSwitchNewProjectSubTab = window.switchNewProjectSubTab || function() {};
    switchNewProjectSubTab = function(tabId, btn) {
        originalSwitchNewProjectSubTab(tabId, btn);
        setTimeout(function() { 
            detectTranscripts();
            updateCopyButtonsVisibility();
        }, 100);
    };

    // Re-detect immediately when transcript fields are edited or pasted.
    document.addEventListener('input', function(event) {
        if (event.target && event.target.matches && event.target.matches('#user_tab_add_entry input, #user_tab_add_entry textarea, #user_tab_add_entry select')) {
            setTimeout(detectTranscripts, 50);
        }
    });
    document.addEventListener('change', function(event) {
        if (event.target && event.target.matches && event.target.matches('#user_tab_add_entry input, #user_tab_add_entry textarea, #user_tab_add_entry select')) {
            setTimeout(detectTranscripts, 50);
        }
    });

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        startTranscriptDetection();
        setTimeout(function() {
            if (typeof updateCopyButtonsVisibility === 'function') {
                updateCopyButtonsVisibility();
            }
        }, 500);
    });
</script>

<script>
/* Coordinate sticky navigation so exactly one row owns the top position. */
(function () {
    function initSingleWinnerStickyTabs() {
        var root = document.getElementById('user_tab_add_entry');
        var scrollHost = document.querySelector('.scroll-body');
        var defaultNav = document.querySelector('.user-config-tabs');
        if (!root || !scrollHost || !defaultNav) return;

        var childSentinels = new Map();
        var mainSentinel = null;
        var scheduled = false;

        function visible(el) {
            return !!(el && el.getClientRects().length &&
                getComputedStyle(el).display !== 'none' &&
                getComputedStyle(el).visibility !== 'hidden');
        }

        function ensureMainSentinel() {
            var nav = root.querySelector('#newProjectSubTabs');
            if (!nav) return null;
            if (mainSentinel && mainSentinel.isConnected && mainSentinel.nextElementSibling === nav) {
                return mainSentinel;
            }
            mainSentinel = document.createElement('span');
            mainSentinel.className = 'main-tab-sticky-sentinel';
            mainSentinel.setAttribute('aria-hidden', 'true');
            mainSentinel.style.cssText = 'display:block;height:1px;width:100%;margin:0;padding:0;pointer-events:none;';
            nav.parentNode.insertBefore(mainSentinel, nav);
            return mainSentinel;
        }

        function ensureChildSentinel(nav) {
            var sentinel = childSentinels.get(nav);
            if (sentinel && sentinel.isConnected && sentinel.nextElementSibling === nav) return sentinel;
            sentinel = document.createElement('span');
            sentinel.className = 'nested-tab-sticky-sentinel';
            sentinel.setAttribute('aria-hidden', 'true');
            sentinel.style.cssText = 'display:block;height:1px;width:100%;margin:0;padding:0;pointer-events:none;';
            nav.parentNode.insertBefore(sentinel, nav);
            childSentinels.set(nav, sentinel);
            return sentinel;
        }

        function updatePriority() {
            scheduled = false;
            var hostTop = scrollHost.getBoundingClientRect().top;
            var rootVisible = visible(root);
            var mainNav = root.querySelector('#newProjectSubTabs');
            var mainHasReachedTop = false;

            if (rootVisible && mainNav && visible(mainNav)) {
                var mainSentinelEl = ensureMainSentinel();
                if (mainSentinelEl) {
                    var mainRect = mainSentinelEl.getBoundingClientRect();
                    mainHasReachedTop = mainRect.bottom <= hostTop;
                }
            }

            defaultNav.classList.toggle('default-nav-released', mainHasReachedTop);

            var childHasReachedTop = false;
            if (rootVisible) {
                root.querySelectorAll('.nested-project-tabs > .dynamic-sub-tabs').forEach(function (nav) {
                    var content = nav.closest('.dynamic-sub-tab-content');
                    if (!visible(nav) || (content && !content.classList.contains('active'))) return;
                    var sentinel = ensureChildSentinel(nav);
                    var rect = sentinel.getBoundingClientRect();
                    if (rect.bottom <= hostTop) childHasReachedTop = true;
                });
            }

            root.classList.toggle('child-nav-priority', childHasReachedTop);
        }

        function scheduleUpdate() {
            if (scheduled) return;
            scheduled = true;
            requestAnimationFrame(updatePriority);
        }

        function refreshSentinels() {
            ensureMainSentinel();
            root.querySelectorAll('.nested-project-tabs > .dynamic-sub-tabs').forEach(ensureChildSentinel);
            scheduleUpdate();
        }

        scrollHost.addEventListener('scroll', scheduleUpdate, { passive: true });
        window.addEventListener('resize', scheduleUpdate, { passive: true });

        if ('MutationObserver' in window) {
            var observer = new MutationObserver(function () {
                refreshSentinels();
            });
            observer.observe(root, {
                subtree: true,
                childList: true,
                attributes: true,
                attributeFilter: ['class']
            });
            observer.observe(defaultNav, {
                attributes: true,
                attributeFilter: ['class']
            });
        }

        refreshSentinels();
        setTimeout(refreshSentinels, 150);
        setTimeout(refreshSentinels, 500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSingleWinnerStickyTabs);
    } else {
        initSingleWinnerStickyTabs();
    }
})();</script>



<script>
/* Enforce the exact sticky-row height equation:
   default tabs = main dynamic tabs - 1px
   main dynamic tabs = nested sub-tabs - 1px
   The main dynamic row remains the reference height; sticky hand-off is unchanged.
*/
(function () {
    function initStickyNavHeightHierarchy() {
        var root = document.getElementById('user_tab_add_entry');
        var defaultNav = document.querySelector('.user-config-tabs');
        if (!root || !defaultNav) return;

        var scheduled = false;

        function syncHeights() {
            scheduled = false;
            var mainNav = root.querySelector('#newProjectSubTabs');
            if (!mainNav) return;

            var mainHeight = mainNav.getBoundingClientRect().height;
            if (!mainHeight || !isFinite(mainHeight)) return;

            var defaultHeight = Math.max(0, mainHeight - 1);
            var nestedHeight = mainHeight + 1;

            function setPx(el, property, value) {
                var px = value + 'px';
                if (el.style.getPropertyValue(property) !== px) {
                    el.style.setProperty(property, px);
                }
            }

            setPx(defaultNav, 'height', defaultHeight);
            setPx(defaultNav, 'min-height', defaultHeight);
            defaultNav.style.setProperty('align-items', 'center', 'important');

            root.querySelectorAll('.nested-project-tabs > .dynamic-sub-tabs').forEach(function (childNav) {
                setPx(childNav, '--nested-sticky-nav-height', nestedHeight);
                setPx(childNav, 'height', nestedHeight);
                setPx(childNav, 'min-height', nestedHeight);
                childNav.style.setProperty('align-items', 'center', 'important');
            });
        }

        function scheduleSync() {
            if (scheduled) return;
            scheduled = true;
            requestAnimationFrame(syncHeights);
        }

        syncHeights();
        window.addEventListener('resize', scheduleSync, { passive: true });

        if ('ResizeObserver' in window) {
            var resizeObserver = new ResizeObserver(scheduleSync);
            var mainNav = root.querySelector('#newProjectSubTabs');
            if (mainNav) resizeObserver.observe(mainNav);
        }

        if ('MutationObserver' in window) {
            var mutationObserver = new MutationObserver(scheduleSync);
            mutationObserver.observe(root, {
                subtree: true,
                childList: true,
                attributes: true,
                attributeFilter: ['class', 'style']
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStickyNavHeightHierarchy, { once: true });
    } else {
        initStickyNavHeightHierarchy();
    }
})();
</script>

<style id="sceneiq-folder-navigation-style">
/* SceneIQ folder/file navigation */
.main-header.folder-mode{justify-content:center;position:relative;min-height:64px;padding:12px 72px}
.main-header.folder-mode .folder-header-left{position:absolute;left:16px;top:50%;transform:translateY(-50%)}
.main-header.folder-mode .folder-header-title{font-size:17px;font-weight:750;text-align:center;max-width:100%;overflow-wrap:anywhere}
.main-header.folder-mode .folder-header-right{position:absolute;right:16px;top:50%;transform:translateY(-50%)}
.folder-back-btn{width:40px;height:40px;border:1px solid rgba(255,255,255,.35);border-radius:12px;background:rgba(255,255,255,.15);color:#fff;font-size:24px;line-height:1;cursor:pointer;display:grid;place-items:center}
.folder-back-btn:hover{background:rgba(255,255,255,.27)}
.folder-nav-root{width:100%;max-width:1100px;margin:0 auto;padding:clamp(14px,3vw,30px) 0 35px}
.folder-nav-heading{margin:0 0 7px;color:#102a43;font-size:clamp(21px,3vw,28px);font-weight:800;letter-spacing:-.035em}
.folder-nav-description{color:#718096;font-size:13px;margin:0 0 22px;line-height:1.6}
.folder-card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.folder-card{appearance:none;position:relative;min-width:0;min-height:142px;text-align:left;padding:20px 18px;border:1px solid #e2e8f0;border-radius:18px;background:linear-gradient(145deg,#fff 0%,#f8fbfc 100%);box-shadow:0 5px 18px rgba(15,35,55,.055);cursor:pointer;display:flex;flex-direction:column;align-items:flex-start;justify-content:space-between;gap:17px;color:#142b3c;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;overflow:hidden}
.folder-card:before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:var(--folder-accent,#0f8b80);opacity:.85}
.folder-card:hover{transform:translateY(-3px);border-color:#9bd7ce;box-shadow:0 12px 28px rgba(15,75,80,.11)}
.folder-card:focus-visible{outline:3px solid #79d3c6;outline-offset:3px}
.folder-card-top{display:flex;width:100%;align-items:flex-start;justify-content:space-between;gap:12px}
.folder-card-icon{width:43px;height:43px;flex:0 0 43px;border-radius:13px;background:var(--folder-tint,#e6f7f4);display:grid;place-items:center;font-size:22px}
.folder-card-arrow{color:#91a2b2;font-size:20px}
.folder-card-title{font-size:15px;font-weight:780;line-height:1.35;overflow-wrap:anywhere}
.folder-card-subtitle{margin-top:5px;font-size:12px;line-height:1.45;color:#81909e;overflow-wrap:anywhere}
.folder-card.wide{grid-column:1/-1;min-height:112px}
.folder-card.wide .folder-card-top{align-items:center}
.folder-card.wide .folder-card-copy{flex:1;min-width:0}
.folder-card-count{font-size:11px;font-weight:750;color:#087f75;background:#e6f7f4;border-radius:99px;padding:5px 9px;white-space:nowrap}
.folder-page-content{min-width:0;width:100%;animation:folderPageIn .18s ease both}
.folder-page-content .user-config-content{display:block!important;padding-top:0}
.folder-page-content .user-config-content.folder-active-content{display:block!important}
.folder-page-content .dynamic-sub-tabs,.folder-page-content .nested-project-tabs>.dynamic-sub-tabs{display:none!important}
.folder-page-content .dynamic-sub-tab-content{display:none!important}
.folder-page-content .dynamic-sub-tab-content.folder-active-content{display:block!important}
.folder-page-content .nested-child-content{display:none!important}
.folder-page-content .nested-child-content.folder-active-content{display:block!important}
.folder-breadcrumb{font-size:12px;color:#8a9aa9;margin-bottom:15px;overflow-wrap:anywhere}
.folder-breadcrumb span{color:#087f75;font-weight:700}
@keyframes folderPageIn{from{opacity:.4;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:560px){.folder-card-grid{gap:10px}.folder-card{min-height:128px;padding:15px 13px;border-radius:15px}.folder-card-icon{width:37px;height:37px;flex-basis:37px;font-size:19px}.folder-card-title{font-size:13px}.folder-card-subtitle{font-size:11px}.main-header.folder-mode{padding-left:62px;padding-right:62px}.main-header.folder-mode .folder-header-left{left:10px}.main-header.folder-mode .folder-header-right{right:10px}.folder-back-btn{width:38px;height:38px}}
@media(prefers-reduced-motion:reduce){.folder-card,.folder-page-content{animation:none!important;transition:none!important}}

/* FINAL FOLDER-ONLY NAVIGATION OVERRIDES: no tab strips or tab-shaped navigation */
body:has(#sceneiqFolderRoot) .dashboard-tabs,
body:has(#sceneiqFolderRoot) .user-config-tabs,
body:has(#sceneiqFolderRoot) #newProjectSubTabs,
body:has(#sceneiqFolderRoot) .folder-page-content .dynamic-sub-tabs,
body:has(#sceneiqFolderRoot) .folder-page-content .nested-project-tabs > .dynamic-sub-tabs {
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    min-height:0 !important;
    max-height:0 !important;
    margin:0 !important;
    padding:0 !important;
    border:0 !important;
    overflow:hidden !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .user-config-content {
    display:block !important;
    width:100%;
    padding:0 !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .dynamic-sub-tab-content {
    display:none !important;
    width:100%;
    padding:0 !important;
    border:0 !important;
    background:transparent !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .dynamic-sub-tab-content.folder-active-content {
    display:block !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .nested-child-content {
    display:none !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .nested-child-content.folder-active-content {
    display:block !important;
}
body:has(#sceneiqFolderRoot) .folder-page-content .folder-page-content {
    width:100%;
    max-width:100%;
    padding:0;
    margin:0;
}
body:has(#sceneiqFolderRoot) .folder-nav-root {
    padding-top:20px;
}
@media(max-width:560px) {
    body:has(#sceneiqFolderRoot) .folder-nav-root { padding-top:14px; }
}
</style>
<script id="sceneiq-folder-navigation">
(function(){
'use strict';
function initSceneIQFolderNavigation(){
 const header=document.querySelector('.main-header');
 const contentArea=document.querySelector('.content-area');
 const originalTabs=document.querySelector('.user-config-tabs');
 if(!header||!contentArea||!originalTabs||!document.getElementById('user_tab_add_entry')) return;
 if(document.getElementById('sceneiqFolderRoot')) return;

 const contentIds=['add_entry','pending','completed','aborted'];
 const labels={add_entry:'New Project',pending:'Pending',completed:'Completed',aborted:'Aborted'};
 const icons={add_entry:'✦',pending:'◷',completed:'✓',aborted:'×'};
 const accents={add_entry:['#0f8b80','#e5f7f3'],pending:['#d99416','#fff5dd'],completed:['#169b72','#e4f8ef'],aborted:['#e05252','#fff0f0']};
 const mainHeaderContent=header.innerHTML;
 const scrollBody=document.querySelector('.scroll-body');
 const root=document.createElement('div'); root.id='sceneiqFolderRoot';root.className='folder-nav-root';
 const page=document.createElement('div');page.id='sceneiqFolderPage';page.className='folder-page-content';
 root.appendChild(page);
 contentArea.insertBefore(root,originalTabs);
 const parking=document.createElement('div');parking.id='sceneiqFolderParking';parking.hidden=true;contentArea.appendChild(parking);
 originalTabs.style.display='none';
 contentIds.forEach(id=>{const el=document.getElementById('user_tab_'+id);if(el){el.classList.remove('active');el.style.display='none';parking.appendChild(el);}});
 function clearPage(){
   contentIds.forEach(id=>{
     const node=document.getElementById('user_tab_'+id);
     if(node && node.parentNode!==parking){node.classList.remove('active');node.style.display='none';parking.appendChild(node);}
   });
   page.innerHTML='';
 }
 // Ensure only the selected account's own content is presented in this view.
 const flashNodes=scrollBody?Array.from(scrollBody.querySelectorAll('.notification')):[];
 flashNodes.forEach(n=>n.style.display='none');

 let stack=[];
 let currentTitle='';
 let currentRender=null;
 function setHeader(title,rootMode){
   header.classList.toggle('folder-mode',!rootMode);
   if(rootMode){header.innerHTML=mainHeaderContent;return;}
   header.innerHTML='<div class="folder-header-left"><button type="button" class="folder-back-btn" aria-label="Go back" title="Go back">‹</button></div><div class="folder-header-title"></div>';
   header.querySelector('.folder-header-title').textContent=title;
   header.querySelector('.folder-back-btn').addEventListener('click',goBack);
 }
 function showCards(title,description,cards,rootMode){
   currentTitle=title;setHeader(title,rootMode);
   clearPage();
   const h=document.createElement('h2');h.className='folder-nav-heading';h.textContent=title;page.appendChild(h);
   if(description){const p=document.createElement('p');p.className='folder-nav-description';p.textContent=description;page.appendChild(p);}
   const grid=document.createElement('div');grid.className='folder-card-grid';
   cards.forEach(c=>{
     const b=document.createElement('button');b.type='button';b.className='folder-card'+(c.wide?' wide':'');
     b.style.setProperty('--folder-accent',c.accent||'#0f8b80');b.style.setProperty('--folder-tint',c.tint||'#e5f7f3');
     b.innerHTML='<div class="folder-card-top"><span class="folder-card-icon" aria-hidden="true"></span><span class="folder-card-arrow" aria-hidden="true">↗</span></div><div class="folder-card-copy"><div class="folder-card-title"></div><div class="folder-card-subtitle"></div></div>';
     b.querySelector('.folder-card-icon').textContent=c.icon||'▰';
     b.querySelector('.folder-card-title').textContent=c.title;
     b.querySelector('.folder-card-subtitle').textContent=c.subtitle||'Open';
     if(c.count!==undefined){const count=document.createElement('span');count.className='folder-card-count';count.textContent=String(c.count);b.querySelector('.folder-card-top').appendChild(count);}
     b.addEventListener('click',c.open);grid.appendChild(b);
   });
   page.appendChild(grid);
 }
 function navigate(render){if(currentRender)stack.push(currentRender);currentRender=render;render();}
 function goBack(){if(!stack.length)return;currentRender=stack.pop();currentRender();}
 function baseCards(){
   const cards=contentIds.map(id=>{
     const pair=accents[id];let subtitle='';
     if(id==='add_entry')subtitle='Start a new project';
     if(id==='pending')subtitle='Projects awaiting action';
     if(id==='completed')subtitle='Finished projects';
     if(id==='aborted')subtitle='Stopped or cancelled projects';
     if(id==='dynamic_tabs')subtitle='Organise project steps';
     if(id==='submit_tabs')subtitle='Choose which tab data is submitted';
     if(id==='dynamic_fields')subtitle='Manage account fields';
     return {title:labels[id],subtitle,icon:icons[id],accent:pair[0],tint:pair[1],open:()=>openTop(id)};
   });
   return cards;
 }
 function rootPage(){stack=[];currentRender=rootPage;showCards('Workspace','Choose a folder to continue. Each view opens on its own, with a back path to the previous location.',baseCards(),true);}
 function openTop(id){
   if(id==='add_entry'){openNewProjectRoot();return;}
   const render=()=> {
     const el=document.getElementById('user_tab_'+id);
     if(!el)return;
     // Only member-facing project and status views are available here.
     if(typeof switchUserConfigTab==='function')switchUserConfigTab(id,null);
     showContentPage(labels[id],el,()=>{});
   };
   navigate(render);
 }
 function showContentPage(title,el,after){
   setHeader(title,false);clearPage();
   const shell=document.createElement('div');shell.className='folder-page-content';page.appendChild(shell);
   contentIds.forEach(id=>{const node=document.getElementById('user_tab_'+id);if(node){node.classList.remove('active');node.style.display='none';}});
   el.style.display='block';el.classList.add('active');shell.appendChild(el);
   after&&after();
 }
 function escapeHtml(s){return String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
 function openNewProjectRoot(){
   const render=()=>{
     const buttons=Array.from(document.querySelectorAll('#newProjectSubTabs .dynamic-sub-tab-btn'));
     const cards=[];
     buttons.forEach((btn,index)=>{
       if(btn.offsetParent===null && getComputedStyle(btn).display==='none')return;
       const tabId=btn.getAttribute('data-tab')||'';
       const title=(btn.textContent||'').trim()||('Project section '+(index+1));
       cards.push({title,subtitle:'Open this project section',icon:'▰',accent:'#0f8b80',tint:'#e5f7f3',open:()=>openDynamicTab(tabId,title)});
     });
     if(!cards.length){
       const el=document.getElementById('user_tab_add_entry');
       showContentPage('New Project',el,()=>{});
       return;
     }
     showCards('New Project','Choose a project section. The global header now shows only your current location and the back button.',cards,false);
   };
   navigate(render);
 }
 function openDynamicTab(tabId,title){
   navigate(()=>{
     const el=document.getElementById('user_tab_add_entry');
     showContentPage(title,el,()=>{
       const nav=document.getElementById('newProjectSubTabs');if(nav)nav.style.display='none';
       document.querySelectorAll('#user_tab_add_entry .dynamic-sub-tab-content').forEach(n=>{n.classList.remove('folder-active-content');n.style.display='none';});
       const target=document.getElementById('newProjectSubTab_'+tabId);
       if(!target)return;
       target.classList.add('folder-active-content');target.style.display='block';
       const nested=target.querySelector('.nested-project-tabs');
       if(nested){
         const childButtons=Array.from(nested.querySelectorAll('.nested-child-btn'));
         const childContents=Array.from(nested.querySelectorAll('.nested-child-content'));
         if(childButtons.length){
           const cards=childButtons.map((btn,i)=>({title:(btn.textContent||'').trim()||('Section '+(i+1)),subtitle:'Open this section',icon:'▰',accent:'#6575db',tint:'#eef0ff',open:()=>openNested(target,nested,btn,i,title)}));
           showCards(title,'Choose a section within '+title+'.',cards,false);
           return;
         }
       }
       // If no nested navigation exists, display the selected tab content directly.
       target.style.display='block';
       const headerTitle=header.querySelector('.folder-header-title');if(headerTitle)headerTitle.textContent=title;
     });
   });
 }
 function openNested(parent,nested,btn,index,parentTitle){
   navigate(()=>{
     const children=Array.from(nested.querySelectorAll('.nested-child-content'));
     const child=children[index];
     const title=(btn.textContent||'').trim()||'Section';
     const el=document.getElementById('user_tab_add_entry');
     showContentPage(title,el,()=>{
       const nav=document.getElementById('newProjectSubTabs');if(nav)nav.style.display='none';
       document.querySelectorAll('#user_tab_add_entry .dynamic-sub-tab-content').forEach(n=>{n.classList.remove('folder-active-content');n.style.display='none';});
       parent.classList.add('folder-active-content');parent.style.display='block';
       nested.querySelectorAll('.dynamic-sub-tabs').forEach(n=>n.style.display='none');
       children.forEach(n=>{n.classList.remove('folder-active-content');n.style.display='none';});
       if(child){child.classList.add('folder-active-content');child.style.display='block';}
       const headerTitle=header.querySelector('.folder-header-title');if(headerTitle)headerTitle.textContent=title;
     });
   });
 }
 rootPage();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initSceneIQFolderNavigation,{once:true});
else initSceneIQFolderNavigation();
})();
</script>

</body>
</html>
