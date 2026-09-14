// lib/screens/admin_screen.dart
// ─────────────────────────────────────────────────────────────────────────────
// Admin panel on mobile — Manage users and view global alert history.
// Accessible when logged in as Admin (9899654695).
// ─────────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/db_service.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<AppUser> _users = [];
  List<Map<String, dynamic>> _history = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final users = await DbService.getAllUsers();
      final history = await DbService.getAlertHistory(1, limit: 30);
      if (mounted) {
        setState(() {
          _users = users;
          _history = history;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _showAddUserDialog() async {
    final phoneCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    bool isAdmin = false;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF161B22),
          title: const Text('Add New User'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: phoneCtrl,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Phone Number', hintText: '9818011930'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Display Name', hintText: 'Mehboob Khan'),
              ),
              const SizedBox(height: 12),
              CheckboxListTile(
                title: const Text('Grant Admin Rights'),
                value: isAdmin,
                activeColor: const Color(0xFF00D4AA),
                onChanged: (v) => setDialogState(() => isAdmin = v ?? false),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel', style: TextStyle(color: Color(0xFF8B949E))),
            ),
            ElevatedButton(
              onPressed: () async {
                if (phoneCtrl.text.isNotEmpty && nameCtrl.text.isNotEmpty) {
                  await DbService.createUser(phoneCtrl.text, nameCtrl.text, isAdmin: isAdmin);
                  Navigator.pop(ctx);
                  _loadData();
                }
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF00D4AA);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Console'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: primary,
          labelColor: primary,
          unselectedLabelColor: const Color(0xFF8B949E),
          tabs: const [
            Tab(icon: Icon(Icons.people_alt_rounded), text: 'Users'),
            Tab(icon: Icon(Icons.history_rounded), text: 'Alert Logs'),
          ],
        ),
      ),
      floatingActionButton: _tabController.index == 0
          ? FloatingActionButton(
              backgroundColor: primary,
              foregroundColor: Colors.black,
              onPressed: _showAddUserDialog,
              child: const Icon(Icons.person_add_rounded),
            )
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: Users
                RefreshIndicator(
                  onRefresh: _loadData,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _users.length,
                    itemBuilder: (ctx, i) {
                      final u = _users[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: u.isAdmin ? primary.withOpacity(0.2) : Colors.blue.withOpacity(0.2),
                            backgroundImage: u.profilePicBytes != null ? MemoryImage(u.profilePicBytes!) : null,
                            child: u.profilePicBytes == null
                                ? Icon(
                                    u.isAdmin ? Icons.security_rounded : Icons.person_rounded,
                                    color: u.isAdmin ? primary : Colors.blueAccent,
                                  )
                                : null,
                          ),
                          title: Text(u.displayName, style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text(u.phone, style: const TextStyle(color: Color(0xFF8B949E))),
                          trailing: u.isAdmin
                              ? const Chip(
                                  label: Text('Admin', style: TextStyle(fontSize: 11, color: Colors.black)),
                                  backgroundColor: primary,
                                )
                              : IconButton(
                                  icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFFF6B6B)),
                                  onPressed: () async {
                                    final confirm = await showDialog<bool>(
                                      context: context,
                                      builder: (c) => AlertDialog(
                                        backgroundColor: const Color(0xFF161B22),
                                        title: const Text('Delete User?'),
                                        content: Text('Remove ${u.displayName}?'),
                                        actions: [
                                          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                                          ElevatedButton(
                                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFFF6B6B)),
                                            onPressed: () => Navigator.pop(c, true),
                                            child: const Text('Delete'),
                                          ),
                                        ],
                                      ),
                                    );
                                    if (confirm == true) {
                                      await DbService.deleteUser(u.id);
                                      _loadData();
                                    }
                                  },
                                ),
                        ),
                      );
                    },
                  ),
                ),

                // Tab 2: Alert History Logs
                RefreshIndicator(
                  onRefresh: _loadData,
                  child: _history.isEmpty
                      ? const Center(child: Text('No alert triggers recorded yet.', style: TextStyle(color: Color(0xFF8B949E))))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _history.length,
                          itemBuilder: (ctx, i) {
                            final h = _history[i];
                            final isAbove = h['alert_type'] == 'above';
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: Icon(
                                  isAbove ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
                                  color: isAbove ? const Color(0xFF238636) : const Color(0xFFDA3633),
                                ),
                                title: Text('${h['symbol']} triggered ${h['alert_type']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Text('Threshold: \$${h['threshold']} • Hit: \$${h['trigger_price']}'),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
