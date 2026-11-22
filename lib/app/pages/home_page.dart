import 'package:flutter/material.dart';
import 'package:lostvault/features/authentication/public/authentication.dart';
import 'package:lostvault/features/objects/public/objects.dart';
import '../composition.dart';
import '../theme.dart';
import '../widgets/action_card.dart';
import '../widgets/object_card.dart';
import 'detail_page.dart';
import 'report_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.session, required this.onLogout});
  final Session session;
  final VoidCallback onLogout;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  ObjectListing _listing = const ObjectListing([]);
  bool _loading = true;
  String? _error;
  String _query = '';
  final _searchFocus = FocusNode();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      _listing = await AppDependencies.instance.search(query: _query);
    } catch (e) {
      _error = e.toString();
    }
    if (mounted) setState(() => _loading = false);
  }

  void _help() => showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Ayuda'),
          content: Text(
              'Sesión: ${widget.session.email}\n\nReporta objetos que encontraste o busca los que perdiste en el campus.'),
          actions: [
            TextButton(
              onPressed: () { Navigator.pop(context); widget.onLogout(); },
              child: const Text('Cerrar sesión'),
            ),
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK')),
          ],
        ),
      );

  Future<void> _goReport() async {
    final ok = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => const ReportPage()));
    if (ok == true) _load();
  }

  Future<void> _goDetail(LostObject o) async {
    final changed = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => DetailPage(obj: o)));
    if (changed == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final items = _listing.items;
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const SizedBox(width: 44),
                Image.asset('assets/images/logo_utb.png', height: 64),
                IconButton.outlined(onPressed: _help, icon: const Icon(Icons.help_outline)),
              ]),
              const SizedBox(height: 16),
              RichText(
                text: const TextSpan(
                  style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: kDark),
                  children: [
                    TextSpan(text: 'Objetos '),
                    TextSpan(text: 'Perdidos', style: TextStyle(color: kBlue)),
                  ],
                ),
              ),
              const SizedBox(height: 6),
              const Text('Reporta o busca objetos extraviados en el campus.',
                  style: TextStyle(fontSize: 16, color: Colors.grey)),
              const SizedBox(height: 20),
              Row(children: [
                Expanded(
                  child: ActionCard(
                    image: 'assets/images/comedor.jpg',
                    chipIcon: Icons.assignment_outlined,
                    chip: 'Nuevo Reporte',
                    title: 'Reportar Objeto',
                    subtitle: 'Sube fotos y detalles de un objeto que encontraste.',
                    action: 'Crear Reporte',
                    onTap: _goReport,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ActionCard(
                    image: 'assets/images/biblioteca.jpg',
                    chipIcon: Icons.search,
                    chip: 'Búsqueda Rápida',
                    title: 'Buscar Objeto',
                    subtitle: 'Navega por la base de datos de objetos encontrados.',
                    action: 'Buscar',
                    onTap: () => _searchFocus.requestFocus(),
                  ),
                ),
              ]),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.grey.shade300),
                  boxShadow: [BoxShadow(color: Colors.black.withOpacity(.05), blurRadius: 10)],
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Encontrados Recientemente',
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: kDark)),
                  const SizedBox(height: 12),
                  TextField(
                    focusNode: _searchFocus,
                    onChanged: (v) { _query = v; _load(); },
                    decoration: InputDecoration(
                      hintText: 'Buscar: Ej. Llaves, Móvil',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (_loading)
                    const Center(
                        child: Padding(
                            padding: EdgeInsets.all(24),
                            child: CircularProgressIndicator()))
                  else if (_error != null)
                    Text(_error!, style: const TextStyle(color: Colors.red))
                  else if (items.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(
                        child: Text('Aún no hay objetos.\nToca "Reportar Objeto" para crear el primero.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.grey)),
                      ),
                    )
                  else
                    GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: items.length,
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12,
                        mainAxisExtent: 190,
                      ),
                      itemBuilder: (_, i) =>
                          ObjectCard(obj: items[i], onTap: () => _goDetail(items[i])),
                    ),
                ]),
              ),
              const SizedBox(height: 24),
              const Center(
                child: Text('© 2026 Universidad Tecnológica de Bolívar',
                    style: TextStyle(color: Colors.grey, fontSize: 12)),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
