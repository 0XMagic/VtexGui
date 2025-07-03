import sys
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showerror, showinfo, showwarning
import uuid
import os
from pathlib import Path
import json
import struct
import subprocess
import shutil


class Config(dict):
	def __init__(self):
		self.path = Path(os.getenv('LOCALAPPDATA')) / "auto_vtex"
		if not self.path.is_dir():
			self.path.mkdir(parents = True)
		super().__init__()
		self.path /= "config.json"
		self._reload()

	def _reload(self):
		self.clear()
		if not self.path.is_file():
			with open(self.path, "w") as fl:
				json.dump(self, fl)

		with open(self.path, "r") as fl:
			for k, v in json.load(fl).items():
				self[k] = v

	def _save(self):
		with open(self.path, "w") as fl:
			json.dump(self, fl)

	@property
	def tf2(self) -> str:
		self._reload()
		return self.get("gamedir", "")

	@tf2.setter
	def tf2(self, value: str):
		self["gamedir"] = value
		self._save()

	@property
	def workshop_export(self):
		self._reload()
		return self.get("export2workshop", False)

	@workshop_export.setter
	def workshop_export(self, value: bool):
		self["export2workshop"] = value
		self._save()

	@property
	def workshop_folder(self):
		self._reload()
		return self.get("workshop_folder", "")

	@workshop_folder.setter
	def workshop_folder(self, value: str):
		self["workshop_folder"] = value
		self._save()

	@property
	def open_explorer(self):
		return self.get("open_explorer", False)

	@open_explorer.setter
	def open_explorer(self, value: bool):
		self["open_explorer"] = value
		self._save()


class TGA:
	def __init__(self, path: Path):
		with open(path, "rb") as fl:
			data = os.read(fl.fileno(), 18)
		self.width, self.height = struct.unpack("hh", data[12:16])


class BoolKVVar:
	def __init__(self, value: bool):
		self.value = value

	def __str__(self):
		return str(int(self.value))

	def __bool__(self):
		return self.value


class VMT:
	def __init__(
			self, material: str,
			shader = "",
			translucent = True,
			vertex_alpha = True,
			vertex_color = True,
			blend_frames = False,
			depth_blend = False,
			depth_blend_scale = 0.0,
			additive = False,
			alpha_test = False,
			no_cull = False,
			over_bright_factor = 0.0,
			custom_path = "",
			custom_folder = "",

	):
		self.shader = shader
		self.base_texture = material
		self.translucent = BoolKVVar(translucent)
		self.vertex_alpha = BoolKVVar(vertex_alpha)
		self.vertex_color = BoolKVVar(vertex_color)
		self.blend_frames = BoolKVVar(blend_frames)
		self.depth_blend = BoolKVVar(depth_blend)
		self.additive = BoolKVVar(additive)
		self.alpha_test = BoolKVVar(alpha_test)
		self.no_cull = BoolKVVar(no_cull)
		self.custom_path = custom_path
		self.folder = custom_folder
		self.over_bright_factor = over_bright_factor
		self.depth_blend_scale = depth_blend_scale


	def __str__(self):
		path = f"{self.base_texture}/{self.base_texture}"
		if self.custom_path:
			path = str(Path(self.custom_path) / f"{self.folder}/{self.base_texture}")

		result = f"\"{self.shader}\" "+"{\n" + "\n".join([
				f"\t\"$basetexture\" \"{path}\"",
				f"\t\"$translucent\" \"{self.translucent}\"" if self.translucent else "",
				f"\t\"$vertexalpha\" \"{self.vertex_alpha}\"" if self.vertex_alpha else "",
				f"\t\"$vertexcolor\" \"{self.vertex_color}\"" if self.vertex_color else "",
				f"\t\"$blendframes\" \"{self.blend_frames}\"" if self.blend_frames else "",
				f"\t\"$depthblend\" \"{self.depth_blend}" if self.depth_blend else "",
				f"\t\"$depthblendscale\" {self.depth_blend_scale}" if self.depth_blend_scale else "",
				f"\t\"$additive\" \"{self.additive}\"" if self.additive else "",
				f"\t\"$alphatest\" \"{self.alpha_test}\"" if self.alpha_test else "",
				f"\t\"$nocull\" \"{self.no_cull}\"" if self.no_cull else "",
				f"\t\"$overbrightfactor\" \"{self.over_bright_factor}\"" if self.over_bright_factor else ""
		]) + "\n}"

		for _ in range(100):
			result = result.replace("\n\n", "\n")
			if "\n\n" not in result: break
		return result


class TF2Output:
	def __init__(self, path: Path, material_name: str, alt_path: str):
		self.tf = path / "tf"
		self.mks = path / "bin/mksheet.exe"
		self.vtex = path / "bin/vtex.exe"
		self.src = path / "tf/materialsrc" / material_name
		self.final = path / "tf/materials" / material_name
		self.alternate_final = path / "tf/materials/effects/workshop" / (alt_path if alt_path else material_name)
		self.material = material_name

	@property
	def exists(self):
		return self.mks.is_file() and self.vtex.is_file()

	def mkdir(self):
		if not self.src.is_dir():
			self.src.mkdir(parents = True)

	def mkdir_alt(self):
		if not self.alternate_final.is_dir():
			self.alternate_final.mkdir(parents = True)


#taken from https://stackoverflow.com/questions/14459993/tkinter-listbox-drag-and-drop-with-python
class DragDropListbox(tk.Listbox):
	def __init__(self, master, **kwargs):
		kwargs['selectmode'] = tk.SINGLE
		self.on_select = kwargs.get("on_select_changed", None)
		if self.on_select is not None:
			kwargs.pop("on_select_changed")

		self.on_order_changed = kwargs.get("on_order_changed", None)
		if self.on_order_changed is not None:
			kwargs.pop("on_order_changed")

		tk.Listbox.__init__(self, master, **kwargs)
		self.bind('<Button-1>', self.setCurrent)
		self.bind('<B1-Motion>', self.shiftSelection)
		self.cur_index = None
		self.cur_uid = None
		self.id_list = list()

	def setCurrent(self, event):
		self.cur_index = self.nearest(event.y)
		if self.cur_index != -1:
			self.cur_uid = self.id_list[self.cur_index]
			if self.on_select:
				self.on_select(self.cur_uid)

	def add(self, item: str):
		self.insert(tk.END, item)
		result = str(uuid.uuid1())
		self.id_list.append(result)
		self.cur_uid = result
		if self.on_select:
			self.on_select(result)
		return result

	def delete_by_uid(self, uid: str):
		index = self.id_list.index(uid)

		self.delete(index)
		self.id_list.pop(index)

		if uid == self.cur_uid:
			if index < len(self.id_list):
				self.cur_uid = self.id_list[index]
			elif self.id_list:
				self.cur_uid = self.id_list[-1]
			else:
				self.cur_uid = None

			if self.on_select:
				self.on_select(self.cur_uid)

	def edit_name(self, uid: str, name: str):
		if not name: name = "<empty>"
		index = self.id_list.index(uid)
		self.delete(index)
		self.insert(index, name)

	def get_by_uid(self, uid: str):
		return self.get(self.id_list.index(uid))

	def shiftSelection(self, event):
		i = self.nearest(event.y)
		if i < self.cur_index:
			x = self.get(i)
			self.delete(i)
			self.insert(i + 1, x)

			x = self.id_list.pop(i)
			self.id_list.insert(i + 1, x)

			self.cur_index = i
			if self.on_order_changed: self.on_order_changed()
		elif i > self.cur_index:
			x = self.get(i)
			self.delete(i)
			self.insert(i - 1, x)

			x = self.id_list.pop(i)
			self.id_list.insert(i - 1, x)

			self.cur_index = i
			if self.on_order_changed: self.on_order_changed()


class SequenceMenu(tk.Frame):
	def __init__(self, master, **kwargs):
		super().__init__(master, **kwargs)

		self.seqs_frame = tk.Frame(self)
		self.v_mat_name = tk.StringVar()
		self.v_mat_name.set("Unnamed_material")
		self.mat_name = tk.Entry(self.seqs_frame, textvariable = self.v_mat_name)
		self.seqs = DragDropListbox(
				self.seqs_frame, width = 120, height = 25,
				on_select_changed = self.seq_change_selection
		)
		self.files_frame = tk.Frame(self)
		self.files_frame_top = tk.Frame(self.files_frame, width = 120)
		self.files = DragDropListbox(
				self.files_frame, width = 120, height = 25,
				on_order_changed = self.update_files_order
		)
		self.data_paths = dict()
		self.data_looping = dict()

		self.buttons = tk.Frame(self.seqs_frame)
		self.file_buttons = tk.Frame(self.files_frame)
		self.v_seq_name = tk.StringVar()
		self.v_seq_name.trace_add("write", self.edit_sequence_name)
		self.seq_name = tk.Entry(self.files_frame, textvariable = self.v_seq_name)
		self.v_looping = tk.BooleanVar(value = True)
		self.v_looping.trace_add("write", self.update_looping)
		self.looping = tk.Checkbutton(self.file_buttons, variable = self.v_looping, text = "Looping")

		self.add = tk.Button(self.buttons, text = "Add sequence", command = self.add_sequence)
		self.remove = tk.Button(self.buttons, text = "Delete sequence", command = self.remove_sequence)

		self.file_add = tk.Button(self.file_buttons, text = "Add images", command = self.add_file_popup)
		self.file_remove = tk.Button(self.file_buttons, text = "Remove image", command = self.remove_image)

		self.seqs_frame.pack(side = "left", anchor = "n", fill = "y")
		self.files_frame.pack(side = "right", anchor = "n", fill = "x")

		self.mat_name.pack(side = "top", fill = "x")
		self.seq_name.pack(side = "top", fill = "x")
		self.looping.pack(side = "top", fill = "x")
		self.files.pack(side = "top")
		self.seqs.pack(side = "top")
		self.buttons.pack(side = "bottom")
		self.file_buttons.pack(side = "bottom")
		self.add.pack(side = "left")
		self.remove.pack(side = "right")
		self.file_add.pack(side = "left")
		self.file_remove.pack(side = "right")

	def add_sequence(self, name: str = None, files: list = None):
		uid = self.seqs.add("New sequence")
		name = f"Sequence {uid}" if not name else name
		self.seqs.edit_name(uid, name)
		index = tk.END
		self.seqs.select_clear(0, "end")
		self.seqs.selection_set(index)
		self.seqs.see(index)
		self.seqs.activate(index)
		self.seqs.selection_anchor(index)

		self.v_seq_name.set(name)
		self.data_looping[uid] = True
		if files:
			self.add_files(*files)

		return uid

	def remove_sequence(self):
		uid = self.seqs.cur_uid
		if not uid:
			self.v_seq_name.set("")
			return

		if uid in self.data_paths:
			self.data_paths.pop(uid)
		if uid in self.data_looping:
			self.data_looping.pop(uid)

		self.seqs.delete_by_uid(uid)
		index = tk.END
		self.seqs.select_clear(0, "end")
		self.seqs.selection_set(index)
		self.seqs.see(index)
		self.seqs.activate(index)
		self.seqs.selection_anchor(index)

	def seq_change_selection(self, uid):
		self.files.delete(0, tk.END)
		if uid is None:
			self.v_seq_name.set("")
			return

		if uid not in self.data_paths:
			self.data_paths[uid] = list()

		if uid not in self.data_looping:
			self.data_looping[uid] = True

		index = self.seqs.id_list.index(uid)
		r = self.seqs.get(index)
		self.v_seq_name.set(r)
		self.v_looping.set(self.data_looping[uid])

		for path in self.data_paths[uid]:
			self.files.add(path)

	def edit_sequence_name(self, *_args):
		uid = self.seqs.cur_uid
		if not uid:
			self.v_seq_name.set("")
			return
		self.seqs.edit_name(uid, self.v_seq_name.get())

	def add_file_popup(self):
		if self.seqs.cur_uid is None:
			return
		result = list(fd.askopenfilenames(
				filetypes = (("Targa files", ".tga"),)
		))
		result.sort()
		self.add_files(*result)
		index = tk.END
		self.files.select_clear(0, tk.END)
		self.files.selection_set(index)
		self.files.see(index)
		self.files.activate(index)
		self.files.selection_anchor(index)

	def add_files(self, *files):
		for file in files:
			self.files.add(file)
			self.data_paths[self.seqs.cur_uid].append(file)

	def remove_image(self):
		file_uid = self.files.cur_uid
		seq_uid = self.seqs.cur_uid
		if file_uid is None or seq_uid is None:
			return

		self.data_paths[seq_uid].remove(self.files.get(self.files.id_list.index(file_uid)))
		self.files.delete_by_uid(file_uid)

		index = tk.END
		self.files.select_clear(0, "end")
		self.files.selection_set(index)
		self.files.see(index)
		self.files.activate(index)
		self.files.selection_anchor(index)

	def update_files_order(self):
		uid = self.seqs.cur_uid
		if uid is None: return

		self.data_paths[uid].clear()
		for i in range(self.files.size()):
			self.data_paths[uid].append(self.files.get(i))

	def update_looping(self, *_args):
		uid = self.seqs.cur_uid
		if not uid:
			self.v_looping.set(False)
			return
		self.data_looping[uid] = self.v_looping.get()


class PageMain(tk.Frame):
	def __init__(self, master, **kwargs):
		super().__init__(master, **kwargs)

		self.builder = SequenceMenu(self, pady = 5)
		self.btn_export = tk.Button(
				self, text = "MAKE VTF", bg = "lightgreen", activebackground = "green", height = 2,
				font = 24, command = self.export
		)
		self.builder.pack(side = "top")
		self.btn_export.pack(side = "bottom", fill = "x")
		self.vmt: [VMTEdit, None] = None

	@staticmethod
	def ask_tf_dir(config: Config):
		showinfo(
				"TF2 Directory not found",
				"A file dialog will now open\nPlease select [steamapps/common/Team Fortress 2]"
		)
		config.tf2 = fd.askdirectory(initialdir = "/")

	def export(self):
		errors = list()
		to_mks = list()

		config = Config()
		asked = False
		custom_path = config.workshop_folder

		if not os.path.isdir(config.tf2):
			asked = True
			self.ask_tf_dir(config)

		tf2 = TF2Output(Path(config.tf2), self.builder.v_mat_name.get(), config.workshop_folder)
		if not tf2.material or any(x in tf2.material for x in "<>:\"/\\|?*"):
			errors.append("Invalid material name.")

		if any(x in custom_path for x in "<>:\"/\\|?*"):
			errors.append("Invalid workshop folder name.")

		if not tf2.exists:
			if not asked:
				self.ask_tf_dir(config)
			tf2 = TF2Output(Path(config.tf2), self.builder.v_mat_name.get(), config.workshop_folder)
			if not tf2.exists:
				errors.append("Team Fortress 2 not found!")

		if not self.builder.seqs.id_list:
			errors.append("No sequences present")

		for uid in self.builder.seqs.id_list:
			if not self.builder.data_paths[uid]:
				errors.append(f"Empty sequence:\n{self.builder.seqs.get_by_uid(uid)}")
				continue
			to_mks.append([self.builder.data_looping[uid]])
			for path in self.builder.data_paths[uid]:
				to_mks[-1].append(path)
				if not os.path.isfile(path):
					errors.append(f"File moved or missing:\n{path}")

		total_images = 0
		size = -1
		err_square = False
		err_mismatch = False

		for seq in to_mks:
			for p in seq[1:]:
				if not os.path.exists(p): continue
				tga = TGA(p)
				if tga.width != tga.height:
					err_square = True
					errors.append(f"File has non-square resolution ({tga.width}x{tga.height})\n{p}")
				total_images += 1
				if size != -1 and size != tga.width and not err_mismatch:
					errors.append(f"Files have different resolutions.")
					err_mismatch = True
				size = tga.width

		if not err_square:
			x = 0
			y = 0

			for i in range(total_images):
				if x + size > 2048:
					y += size
					x = 0
					if y > 2048:
						errors.append("Too much data.\n(Final composite must fit in 2048x2028 texture)")
						break
				else:
					x += size
		mks_lines = list()
		mks_i = 0
		for sequence in to_mks:
			looping = sequence.pop(0)
			mks_lines.append(f"sequence {mks_i}")
			if looping: mks_lines.append("loop")
			mks_i += 1

			for path in sequence:
				mks_lines.append(f"frame {path} 1")

		if errors:
			showerror("VTF ERROR", "The following errors have occurred:\n\n" + "\n\n".join(errors))
			return

		path_mks = Path(tf2.material + ".mks")

		with open(path_mks, "w") as fl:
			fl.write("\n".join(mks_lines))

		subprocess.call(str(tf2.mks) + f" \"{path_mks}\"")
		tf2.mkdir()
		for source, dest in [
				[tf2.material + ".mks", tf2.src / (tf2.material + ".mks")],
				[tf2.material + ".sht", tf2.src / (tf2.material + ".sht")],
				[tf2.material + ".tga", tf2.src / (tf2.material + ".tga")],
		]:
			if dest.is_file():
				os.remove(dest)
			shutil.move(source, dest)

		result_sht = tf2.src / (tf2.material + ".sht")
		subprocess.call(str(tf2.vtex) + f" -nopause -game \"{str(tf2.tf)}\" \"{result_sht}\"")

		custom_export = ""
		if config.workshop_export:
			custom_export = "Effects/workshop/"

		with open(tf2.final / (tf2.material + ".vmt"), "w") as fl:
			assert isinstance(self.vmt, VMTEdit)
			fl.write(str(VMT(
					tf2.material,
					shader = self.vmt.v_shader.get(),
					blend_frames = self.vmt.v_blend_frames.get(),
					depth_blend = self.vmt.v_depth_blend.get(),
					additive = self.vmt.v_additive.get(),
					custom_path = custom_export,
					custom_folder = config.workshop_folder,
					alpha_test = self.vmt.v_alpha_test.get(),
					no_cull = self.vmt.v_no_cull.get(),
					over_bright_factor = self.vmt.over_bright.value,
					vertex_alpha = self.vmt.v_vertex_alpha.get(),
					vertex_color = self.vmt.v_vertex_color.get(),
					depth_blend_scale = self.vmt.depth_blend_scale.value
			)))

		if custom_export:
			tf2.mkdir_alt()
			for source, dest in [
					[tf2.final / f"{tf2.material}.vmt", tf2.alternate_final / f"{tf2.material}.vmt"],
					[tf2.final / f"{tf2.material}.vtf", tf2.alternate_final / f"{tf2.material}.vtf"]
			]:
				if dest.is_file():
					os.remove(dest)
				shutil.move(source, dest)
			tf2.final.rmdir()

		if config.open_explorer:
			os.startfile(tf2.final if not custom_export else tf2.alternate_final)



class FloatField(tk.Frame):
	def __init__(self, master, name: str, default: float = 0.0, **kwargs):
		super().__init__(master, **kwargs)
		self._value = tk.StringVar(value = str(default))
		self._value.trace_add("write", self.update_color)
		self.entry = tk.Entry(self, textvariable = self._value, width = 5)
		self.label = tk.Label(self, text = name)

		self.label.pack(side = "left")
		self.entry.pack(side = "right")


	def update_color(self, *_args):
		try:
			float(self._value.get())
			is_float = True
		except ValueError:
			is_float = False

		if is_float:
			self.entry.config(fg = "black")
		else:
			self.entry.config(fg = "red")




	@property
	def value(self):
		try:
			return float(self._value.get())
		except ValueError:
			return 0.0


class VMTEdit(tk.Frame):
	def __init__(self, master, **kwargs):
		super().__init__(master, **kwargs)

		self.v_shader = tk.StringVar(value = "SpriteCard")
		self.v_translucent = tk.BooleanVar(value = True)
		self.v_vertex_alpha = tk.BooleanVar(value = True)
		self.v_vertex_color = tk.BooleanVar(value = True)
		self.v_blend_frames = tk.BooleanVar()
		self.v_depth_blend = tk.BooleanVar()
		self.v_additive = tk.BooleanVar()
		self.v_alpha_test = tk.BooleanVar()
		self.v_no_cull = tk.BooleanVar()

		self.shader = ttk.Combobox(self, textvariable = self.v_shader, values = ["SpriteCard", "UnlitGeneric"], state = "readonly")
		self.translucent = tk.Checkbutton(self, variable = self.v_translucent, text = "Translucent")
		self.vertex_alpha = tk.Checkbutton(self, variable = self.v_vertex_alpha, text = "Vertex alpha")
		self.vertex_color = tk.Checkbutton(self, variable = self.v_vertex_color, text = "Vertex color")
		self.blend_frames = tk.Checkbutton(self, variable = self.v_blend_frames, text = "Blend frames")
		self.depth_blend = tk.Checkbutton(self, variable = self.v_depth_blend, text = "Depth blend")
		self.depth_blend_scale = FloatField(self, "Depth blend scale", default = 50.0)
		self.additive = tk.Checkbutton(self, variable = self.v_additive, text = "Additive")
		self.alpha_test = tk.Checkbutton(self, variable = self.v_alpha_test, text = "Alpha test")
		self.no_cull = tk.Checkbutton(self, variable = self.v_no_cull, text = "No cull")
		self.over_bright = FloatField(self, "OverBrightFactor")

		self.shader.pack(side = "top")
		self.translucent.pack(side = "top")
		self.vertex_alpha.pack(side = "top")
		self.vertex_color.pack(side = "top")
		self.blend_frames.pack(side = "top")
		self.depth_blend.pack(side = "top")
		self.depth_blend_scale.pack(side = "top")
		self.additive.pack(side = "top")
		self.alpha_test.pack(side = "top")
		self.no_cull.pack(side = "top")
		self.over_bright.pack(side = "top")


class NamedEntry(tk.Frame):
	def __init__(self, master, name: str, default_value: str, **kwargs):
		super().__init__(master, **kwargs)
		self.on_changed = None
		self.v_entry = tk.StringVar(value = default_value)
		self.label = tk.Label(self, text = name)
		self.entry = tk.Entry(self, textvariable = self.v_entry)

		self.label.pack(side = "left")
		self.entry.pack(side = "right", fill = "x")

		self.v_entry.trace_add("write", self._changed)

	def _changed(self, *_args):
		if self.on_changed:
			self.on_changed()


class ConfigFrame(tk.Frame):
	def __init__(self, master, **kwargs):
		super().__init__(master, **kwargs)
		self.v_explorer = tk.BooleanVar()
		self.v_workshop = tk.BooleanVar()
		self.cfg = Config()

		self.workshop_export = tk.Checkbutton(self, text = "Export to workshop folder", variable = self.v_workshop)
		self.v_workshop.set(self.cfg.workshop_export)
		self.v_workshop.trace_add("write", self.changed_custom_dir)

		self.open_explorer = tk.Checkbutton(
				self, text = "Open explorer to exported material",
				variable = self.v_explorer
		)
		self.v_explorer.set(self.cfg.open_explorer)
		self.v_explorer.trace_add("write", self.changed_open_explorer)

		self.workshop_folder = NamedEntry(self, "Workshop folder", self.cfg.workshop_folder)
		self.workshop_folder.on_changed = self.changed_custom_folder

		self.workshop_export.pack(side = "top")
		self.workshop_folder.pack(side = "top")
		self.open_explorer.pack(side = "top")

	def changed_custom_dir(self, *_args):
		self.cfg.workshop_export = self.v_workshop.get()

	def changed_open_explorer(self, *_args):
		self.cfg.open_explorer = self.v_explorer.get()

	def changed_custom_folder(self):
		self.cfg.workshop_folder = self.workshop_folder.v_entry.get()


class DroppedFile:
	def __init__(self, path: Path):
		self.path = path
		self.strpath = str(path)
		self.file = self.strpath.split("\\")[-1]
		self.category = ""
		if "-" in self.file:
			self.category = self.file.split("-")[0]

	def __str__(self):
		return self.strpath


def launch(*paths: str):
	paths = [Path(path) for path in paths]
	non_tga = [str(path) for path in paths if not str(path).lower().endswith(".tga")]
	non_files = [str(path) for path in paths if not path.is_file()]

	paths = [
			DroppedFile(path) for path in paths if
			str(path).lower().endswith("tga") and path.is_file()
	]

	paths.sort(key = lambda path: path.file)

	dropped_files = dict()
	for path in paths:
		if path.category not in dropped_files: dropped_files[path.category] = list()
		dropped_files[path.category].append(path)

	warning_lines = list()

	if non_tga:
		warning_lines.append("The following files were ignored for not being Targa (tga) files:")
		warning_lines += non_tga

	if non_files:
		if non_tga: warning_lines.append("")
		warning_lines.append("The following arguments were not files!")
		warning_lines += non_files

	if warning_lines:
		showwarning("Drag-and-drop Warning", "\n".join(warning_lines))

	app = tk.Tk()
	tabs = ttk.Notebook(app)
	tabs.pack(side = "top")

	cfg = ConfigFrame(tabs)
	vmt_edit = VMTEdit(tabs)
	page = PageMain(tabs)
	tabs.add(page, text = "Sequence editor")
	tabs.add(vmt_edit, text = "Advanced options")
	tabs.add(cfg, text = "Config")
	page.vmt = vmt_edit

	if dropped_files:
		for category, path_list in dropped_files.items():
			page.builder.add_sequence(
					name = category,
					files = [str(path) for path in path_list]
			)
	else:
		page.builder.add_sequence()

	app.mainloop()


def main():
	launch(*(sys.argv[1:] if len(sys.argv) > 1 else list()))


if __name__ == '__main__':
	main()
