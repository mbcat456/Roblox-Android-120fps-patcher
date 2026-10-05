package com.marco.robloxapkm;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.IntentSender;
import android.content.pm.PackageInstaller;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public final class MainActivity extends Activity {
    private static final int REQUEST_PICK_BUNDLE = 10;
    private static final int REQUEST_UNKNOWN_APPS = 20;
    private static final String ACTION_INSTALL_COMPLETE =
        "com.marco.robloxapkm.INSTALL_COMPLETE";

    private TextView statusView;
    private ProgressBar progressBar;
    private Button permissionButton;
    private Button chooseButton;

    private final BroadcastReceiver installComplete = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (!intent.hasExtra(PackageInstaller.EXTRA_STATUS)) {
                return;
            }
            int status = intent.getIntExtra(
                PackageInstaller.EXTRA_STATUS,
                PackageInstaller.STATUS_FAILURE
            );
            String text = statusText(status);
            runOnUiThread(() -> {
                progressBar.setVisibility(View.GONE);
                statusView.setText(getString(R.string.install_result, text));
            });
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusView = findViewById(R.id.status);
        progressBar = findViewById(R.id.progress);
        permissionButton = findViewById(R.id.permission);
        chooseButton = findViewById(R.id.choose);

        chooseButton.setOnClickListener(view -> openFilePicker());
        permissionButton.setOnClickListener(view -> openInstallPermissionSettings());
        registerReceiver(installComplete, new IntentFilter(ACTION_INSTALL_COMPLETE));
        updateInstallPermissionUi();

        Intent launchIntent = getIntent();
        if (Intent.ACTION_VIEW.equals(launchIntent.getAction())
                && launchIntent.getData() != null) {
            installBundle(launchIntent.getData());
        }
    }

    @Override
    protected void onDestroy() {
        unregisterReceiver(installComplete);
        super.onDestroy();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateInstallPermissionUi();
    }

    private void updateInstallPermissionUi() {
        boolean granted = getPackageManager().canRequestPackageInstalls();
        permissionButton.setVisibility(granted ? View.GONE : View.VISIBLE);
        chooseButton.setVisibility(granted ? View.VISIBLE : View.GONE);
        if (!granted) {
            statusView.setText(getString(R.string.permission_needed));
        }
    }

    private void openFilePicker() {
        if (!getPackageManager().canRequestPackageInstalls()) {
            openInstallPermissionSettings();
            return;
        }

        Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        picker.addCategory(Intent.CATEGORY_OPENABLE);
        picker.setType("*/*");
        picker.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
            "application/zip",
            "application/octet-stream"
        });
        startActivityForResult(picker, REQUEST_PICK_BUNDLE);
    }

    private void openInstallPermissionSettings() {
        Intent permission = new Intent(
            android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
            Uri.parse("package:" + getPackageName())
        );
        startActivityForResult(permission, REQUEST_UNKNOWN_APPS);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_UNKNOWN_APPS) {
            updateInstallPermissionUi();
            if (getPackageManager().canRequestPackageInstalls()) {
                statusView.setText(getString(R.string.permission_granted));
                openFilePicker();
            }
            return;
        }
        if (requestCode == REQUEST_PICK_BUNDLE
                && resultCode == RESULT_OK
                && data != null
                && data.getData() != null) {
            installBundle(data.getData());
        }
    }

    private void installBundle(Uri uri) {
        statusView.setText(getString(R.string.preparing));
        progressBar.setVisibility(View.VISIBLE);

        new Thread(() -> {
            try {
                File directory = extractBundle(uri);
                List<File> parts = apkParts(directory);
                installApks(parts);
            } catch (Exception exception) {
                runOnUiThread(() -> {
                    progressBar.setVisibility(View.GONE);
                    statusView.setText(getString(
                        R.string.install_failed,
                        exception.getMessage()
                    ));
                });
            }
        }).start();
    }

    private File extractBundle(Uri uri) throws Exception {
        File bundle = new File(getCacheDir(), "roblox_bundle.apkm");
        try (InputStream input = getContentResolver().openInputStream(uri);
             OutputStream output = new FileOutputStream(bundle)) {
            copy(input, output);
        }

        File directory = new File(getCacheDir(), "bundle_parts");
        deleteRecursively(directory);
        if (!directory.mkdirs()) {
            throw new IllegalStateException("cannot create extraction directory");
        }

        try (ZipFile zip = new ZipFile(bundle)) {
            Enumeration<? extends ZipEntry> entries = zip.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                if (entry.isDirectory() || !entry.getName().toLowerCase().endsWith(".apk")) {
                    continue;
                }
                File target = new File(directory, new File(entry.getName()).getName());
                try (InputStream input = zip.getInputStream(entry);
                     OutputStream output = new FileOutputStream(target)) {
                    copy(input, output);
                }
            }
        }
        return directory;
    }

    private List<File> apkParts(File directory) {
        File base = new File(directory, "base.apk");
        List<File> parts = new ArrayList<>();
        if (base.isFile()) {
            parts.add(base);
        }
        File[] children = directory.listFiles();
        if (children == null) {
            return parts;
        }
        for (File child : children) {
            if (child.isFile()
                    && child.getName().toLowerCase().endsWith(".apk")
                    && !child.getName().equalsIgnoreCase("base.apk")) {
                parts.add(child);
            }
        }
        if (parts.isEmpty()) {
            throw new IllegalStateException("bundle contains no base.apk");
        }
        return parts;
    }

    private void installApks(List<File> parts) throws Exception {
        PackageInstaller installer = getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams params =
            new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        int sessionId = installer.createSession(params);
        PackageInstaller.Session session = installer.openSession(sessionId);

        try {
            for (File part : parts) {
                long size = part.length();
                try (OutputStream output =
                         session.openWrite(part.getName(), 0, size);
                     InputStream input = new FileInputStream(part)) {
                    copy(input, output);
                }
            }

            Intent completion = new Intent(ACTION_INSTALL_COMPLETE);
            completion.setPackage(getPackageName());
            PendingIntent sender = PendingIntent.getBroadcast(
                this,
                sessionId,
                completion,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
            );
            session.commit(sender.getIntentSender());
        } catch (Exception exception) {
            try {
                session.abandon();
            } catch (Exception ignored) {
                // The original installation exception is more useful.
            }
            throw exception;
        } finally {
            session.close();
        }

        runOnUiThread(() -> {
            progressBar.setVisibility(View.GONE);
            statusView.setText(getString(R.string.install_prompt));
        });
    }

    private static void copy(InputStream input, OutputStream output) throws Exception {
        byte[] buffer = new byte[64 * 1024];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
    }

    private static String statusText(int status) {
        switch (status) {
            case PackageInstaller.STATUS_SUCCESS:
                return "success";
            case PackageInstaller.STATUS_PENDING_USER_ACTION:
                return "waiting for user permission";
            case PackageInstaller.STATUS_FAILURE_ABORTED:
                return "aborted";
            case PackageInstaller.STATUS_FAILURE_BLOCKED:
                return "blocked";
            case PackageInstaller.STATUS_FAILURE_CONFLICT:
                return "package conflict";
            case PackageInstaller.STATUS_FAILURE_INCOMPATIBLE:
                return "incompatible package";
            case PackageInstaller.STATUS_FAILURE_INVALID:
                return "invalid package";
            case PackageInstaller.STATUS_FAILURE_STORAGE:
                return "storage failure";
            case PackageInstaller.STATUS_FAILURE_TIMEOUT:
                return "timed out";
            default:
                return "code " + status;
        }
    }

    private static void deleteRecursively(File file) {
        if (!file.exists()) {
            return;
        }
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursively(child);
                }
            }
        }
        file.delete();
    }
}
