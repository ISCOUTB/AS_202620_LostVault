import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:lostvault/features/objects/public/objects.dart';
import '../composition.dart';
import '../theme.dart';

class ReportPage extends StatefulWidget {
  const ReportPage({super.key});
  @override
  State<ReportPage> createState() => _ReportPageState();
}

class _ReportPageState extends State<ReportPage> {
  final _name = TextEditingController();
  final _desc = TextEditingController();
  final _loc = TextEditingController();
  DateTime _date = DateTime.now();
  File? _image;
  bool _loading = false;

  String get _dateStr => _date.toIso8601String().split('T').first;

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<void> _pick(ImageSource s) async {
    final x = await ImagePicker().pickImage(source: s, maxWidth: 1024, imageQuality: 80);
    if (x != null) setState(() => _image = File(x.path));
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
        context: context,
        initialDate: _date,
        firstDate: DateTime(2020),
        lastDate: DateTime.now());
    if (d != null) setState(() => _date = d);
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty || _loc.text.trim().isEmpty) {
      _snack('Nombre y ubicación son obligatorios');
      return;
    }
    setState(() => _loading = true);
    try {
      await AppDependencies.instance.objects.create(ObjectDraft(
        name: _name.text.trim(),
        description: _desc.text.trim(),
        location: _loc.text.trim(),
        foundDate: _dateStr,
        imagePath: _image?.path,
      ));
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        _snack(e.toString());
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Reportar Objeto')),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          GestureDetector(
            onTap: () => showModalBottomSheet(
              context: context,
              builder: (_) => SafeArea(
                child: Wrap(children: [
                  ListTile(
                    leading: const Icon(Icons.camera_alt),
                    title: const Text('Cámara'),
                    onTap: () { Navigator.pop(context); _pick(ImageSource.camera); },
                  ),
                  ListTile(
                    leading: const Icon(Icons.photo_library),
                    title: const Text('Galería'),
                    onTap: () { Navigator.pop(context); _pick(ImageSource.gallery); },
                  ),
                ]),
              ),
            ),
            child: Container(
              height: 180,
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: _image == null
                  ? const Center(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.add_a_photo_outlined, size: 40),
                        SizedBox(height: 8),
                        Text('Agregar foto'),
                      ]),
                    )
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.file(_image!, fit: BoxFit.cover, width: double.infinity)),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
              controller: _name,
              maxLength: 120,
              decoration: const InputDecoration(
                  labelText: 'Nombre del objeto', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(
              controller: _loc,
              decoration: const InputDecoration(
                  labelText: 'Ubicación (Ej. Biblioteca Bloque B)',
                  border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(
              controller: _desc,
              maxLines: 3,
              maxLength: 1000,
              decoration: const InputDecoration(
                  labelText: 'Descripción', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _pickDate,
            icon: const Icon(Icons.calendar_today),
            label: Text('Hallado: $_dateStr'),
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 50,
            child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: kBlue),
              onPressed: _loading ? null : _submit,
              child: _loading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('Crear Reporte'),
            ),
          ),
        ]),
      );
}
