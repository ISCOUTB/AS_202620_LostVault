import 'package:flutter/material.dart';
import 'package:lostvault/features/objects/public/objects.dart';
import '../composition.dart';
import '../theme.dart';
import '../widgets/object_card.dart';

class DetailPage extends StatefulWidget {
  const DetailPage({super.key, required this.obj});
  final LostObject obj;
  @override
  State<DetailPage> createState() => _DetailPageState();
}

class _DetailPageState extends State<DetailPage> {
  bool _busy = false;
  late ObjectStatus _status = widget.obj.status;

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<bool> _confirm(String title, String body, String ok) async =>
      await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(ok)),
          ],
        ),
      ) ??
      false;

  Future<void> _claim() async {
    if (!await _confirm('Reclamar objeto',
        'Verificaremos tu identidad antes de registrar la reclamación.', 'Reclamar')) {
      return;
    }
    setState(() => _busy = true);
    try {
      final c = await AppDependencies.instance.claim(widget.obj.id);
      if (!mounted) return;
      if (c.verified) {
        await AppDependencies.instance.objects.markClaimed(widget.obj.id);
        if (mounted) setState(() => _status = ObjectStatus.claimed);
      }
      _snack('Reclamación verificada');
    } catch (e) {
      _snack(e.toString());
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _delete() async {
    if (!await _confirm('Borrar reporte',
        '¿Seguro que quieres borrar este objeto?', 'Borrar')) {
      return;
    }
    setState(() => _busy = true);
    try {
      await AppDependencies.instance.objects.delete(widget.obj.id);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      _snack(e.toString()); // p. ej. si el reporte no es tuyo
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = widget.obj;
    final available = _status == ObjectStatus.available;
    return Scaffold(
      appBar: AppBar(title: const Text('Detalle')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Center(child: ObjectThumb(path: o.imagePath, size: 220, icon: 60)),
        const SizedBox(height: 16),
        Text(o.name,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: kDark)),
        const SizedBox(height: 4),
        Chip(
          label: Text(available ? 'Disponible' : 'Reclamado'),
          backgroundColor: available ? kChip : Colors.orange.shade100,
        ),
        ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.place_outlined),
            title: Text(o.location)),
        ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.calendar_today),
            title: Text('Hallado: ${o.foundDate}')),
        if (o.description.isNotEmpty) Text(o.description),
        const SizedBox(height: 24),
        SizedBox(
          height: 50,
          child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: kBlue),
            onPressed: (_busy || !available) ? null : _claim,
            icon: const Icon(Icons.back_hand_outlined),
            label: Text(available ? 'Es mío, reclamar' : 'Ya reclamado'),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 50,
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
            onPressed: _busy ? null : _delete,
            icon: const Icon(Icons.delete_outline),
            label: const Text('Borrar mi reporte'),
          ),
        ),
      ]),
    );
  }
}
