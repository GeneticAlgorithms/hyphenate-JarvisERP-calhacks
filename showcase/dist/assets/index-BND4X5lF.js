import{M as oe,O as ge,B as ve,F as ie,S as x,U,V as f,W as $,H as N,N as be,C as we,a as z,b as C,A as ne,c as ye,R as xe,d as Ce,e as Se,L as Te,f as Me,g as Ee,h as Ae,i as Re,j as _e,P as Pe,k as Le,l as Be,I as Ie,m as k,n as De,o as Fe,p as $e,q as Ne}from"./three-D8n-YDYp.js";import{g as B}from"./gsap-SFc2wnMY.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))s(a);new MutationObserver(a=>{for(const i of a)if(i.type==="childList")for(const r of i.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&s(r)}).observe(document,{childList:!0,subtree:!0});function t(a){const i={};return a.integrity&&(i.integrity=a.integrity),a.referrerPolicy&&(i.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?i.credentials="include":a.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(a){if(a.ep)return;a.ep=!0;const i=t(a);fetch(a.href,i)}})();const le={name:"CopyShader",uniforms:{tDiffuse:{value:null},opacity:{value:1}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform float opacity;

		uniform sampler2D tDiffuse;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );
			gl_FragColor = opacity * texel;


		}`};class T{constructor(){this.isPass=!0,this.enabled=!0,this.needsSwap=!0,this.clear=!1,this.renderToScreen=!1}setSize(){}render(){console.error("THREE.Pass: .render() must be implemented in derived pass.")}dispose(){}}const Ue=new ge(-1,1,1,-1,0,1);class ze extends ve{constructor(){super(),this.setAttribute("position",new ie([-1,3,0,-1,-1,0,3,-1,0],3)),this.setAttribute("uv",new ie([0,2,0,0,2,0],2))}}const He=new ze;class V{constructor(e){this._mesh=new oe(He,e)}dispose(){this._mesh.geometry.dispose()}render(e){e.render(this._mesh,Ue)}get material(){return this._mesh.material}set material(e){this._mesh.material=e}}class Oe extends T{constructor(e,t){super(),this.textureID=t!==void 0?t:"tDiffuse",e instanceof x?(this.uniforms=e.uniforms,this.material=e):e&&(this.uniforms=U.clone(e.uniforms),this.material=new x({name:e.name!==void 0?e.name:"unspecified",defines:Object.assign({},e.defines),uniforms:this.uniforms,vertexShader:e.vertexShader,fragmentShader:e.fragmentShader})),this.fsQuad=new V(this.material)}render(e,t,s){this.uniforms[this.textureID]&&(this.uniforms[this.textureID].value=s.texture),this.fsQuad.material=this.material,this.renderToScreen?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this.fsQuad.render(e))}dispose(){this.material.dispose(),this.fsQuad.dispose()}}class se extends T{constructor(e,t){super(),this.scene=e,this.camera=t,this.clear=!0,this.needsSwap=!1,this.inverse=!1}render(e,t,s){const a=e.getContext(),i=e.state;i.buffers.color.setMask(!1),i.buffers.depth.setMask(!1),i.buffers.color.setLocked(!0),i.buffers.depth.setLocked(!0);let r,n;this.inverse?(r=0,n=1):(r=1,n=0),i.buffers.stencil.setTest(!0),i.buffers.stencil.setOp(a.REPLACE,a.REPLACE,a.REPLACE),i.buffers.stencil.setFunc(a.ALWAYS,r,4294967295),i.buffers.stencil.setClear(n),i.buffers.stencil.setLocked(!0),e.setRenderTarget(s),this.clear&&e.clear(),e.render(this.scene,this.camera),e.setRenderTarget(t),this.clear&&e.clear(),e.render(this.scene,this.camera),i.buffers.color.setLocked(!1),i.buffers.depth.setLocked(!1),i.buffers.color.setMask(!0),i.buffers.depth.setMask(!0),i.buffers.stencil.setLocked(!1),i.buffers.stencil.setFunc(a.EQUAL,1,4294967295),i.buffers.stencil.setOp(a.KEEP,a.KEEP,a.KEEP),i.buffers.stencil.setLocked(!0)}}class ke extends T{constructor(){super(),this.needsSwap=!1}render(e){e.state.buffers.stencil.setLocked(!1),e.state.buffers.stencil.setTest(!1)}}class Ge{constructor(e,t){if(this.renderer=e,this._pixelRatio=e.getPixelRatio(),t===void 0){const s=e.getSize(new f);this._width=s.width,this._height=s.height,t=new $(this._width*this._pixelRatio,this._height*this._pixelRatio,{type:N}),t.texture.name="EffectComposer.rt1"}else this._width=t.width,this._height=t.height;this.renderTarget1=t,this.renderTarget2=t.clone(),this.renderTarget2.texture.name="EffectComposer.rt2",this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2,this.renderToScreen=!0,this.passes=[],this.copyPass=new Oe(le),this.copyPass.material.blending=be,this.clock=new we}swapBuffers(){const e=this.readBuffer;this.readBuffer=this.writeBuffer,this.writeBuffer=e}addPass(e){this.passes.push(e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}insertPass(e,t){this.passes.splice(t,0,e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}removePass(e){const t=this.passes.indexOf(e);t!==-1&&this.passes.splice(t,1)}isLastEnabledPass(e){for(let t=e+1;t<this.passes.length;t++)if(this.passes[t].enabled)return!1;return!0}render(e){e===void 0&&(e=this.clock.getDelta());const t=this.renderer.getRenderTarget();let s=!1;for(let a=0,i=this.passes.length;a<i;a++){const r=this.passes[a];if(r.enabled!==!1){if(r.renderToScreen=this.renderToScreen&&this.isLastEnabledPass(a),r.render(this.renderer,this.writeBuffer,this.readBuffer,e,s),r.needsSwap){if(s){const n=this.renderer.getContext(),l=this.renderer.state.buffers.stencil;l.setFunc(n.NOTEQUAL,1,4294967295),this.copyPass.render(this.renderer,this.writeBuffer,this.readBuffer,e),l.setFunc(n.EQUAL,1,4294967295)}this.swapBuffers()}se!==void 0&&(r instanceof se?s=!0:r instanceof ke&&(s=!1))}}this.renderer.setRenderTarget(t)}reset(e){if(e===void 0){const t=this.renderer.getSize(new f);this._pixelRatio=this.renderer.getPixelRatio(),this._width=t.width,this._height=t.height,e=this.renderTarget1.clone(),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.renderTarget1=e,this.renderTarget2=e.clone(),this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2}setSize(e,t){this._width=e,this._height=t;const s=this._width*this._pixelRatio,a=this._height*this._pixelRatio;this.renderTarget1.setSize(s,a),this.renderTarget2.setSize(s,a);for(let i=0;i<this.passes.length;i++)this.passes[i].setSize(s,a)}setPixelRatio(e){this._pixelRatio=e,this.setSize(this._width,this._height)}dispose(){this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.copyPass.dispose()}}class We extends T{constructor(e,t,s=null,a=null,i=null){super(),this.scene=e,this.camera=t,this.overrideMaterial=s,this.clearColor=a,this.clearAlpha=i,this.clear=!0,this.clearDepth=!1,this.needsSwap=!1,this._oldClearColor=new z}render(e,t,s){const a=e.autoClear;e.autoClear=!1;let i,r;this.overrideMaterial!==null&&(r=this.scene.overrideMaterial,this.scene.overrideMaterial=this.overrideMaterial),this.clearColor!==null&&(e.getClearColor(this._oldClearColor),e.setClearColor(this.clearColor)),this.clearAlpha!==null&&(i=e.getClearAlpha(),e.setClearAlpha(this.clearAlpha)),this.clearDepth==!0&&e.clearDepth(),e.setRenderTarget(this.renderToScreen?null:s),this.clear===!0&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),e.render(this.scene,this.camera),this.clearColor!==null&&e.setClearColor(this._oldClearColor),this.clearAlpha!==null&&e.setClearAlpha(i),this.overrideMaterial!==null&&(this.scene.overrideMaterial=r),e.autoClear=a}}const qe={uniforms:{tDiffuse:{value:null},luminosityThreshold:{value:1},smoothWidth:{value:1},defaultColor:{value:new z(0)},defaultOpacity:{value:0}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;

			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform sampler2D tDiffuse;
		uniform vec3 defaultColor;
		uniform float defaultOpacity;
		uniform float luminosityThreshold;
		uniform float smoothWidth;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );

			vec3 luma = vec3( 0.299, 0.587, 0.114 );

			float v = dot( texel.xyz, luma );

			vec4 outputColor = vec4( defaultColor.rgb, defaultOpacity );

			float alpha = smoothstep( luminosityThreshold, luminosityThreshold + smoothWidth, v );

			gl_FragColor = mix( outputColor, texel, alpha );

		}`};class S extends T{constructor(e,t,s,a){super(),this.strength=t!==void 0?t:1,this.radius=s,this.threshold=a,this.resolution=e!==void 0?new f(e.x,e.y):new f(256,256),this.clearColor=new z(0,0,0),this.renderTargetsHorizontal=[],this.renderTargetsVertical=[],this.nMips=5;let i=Math.round(this.resolution.x/2),r=Math.round(this.resolution.y/2);this.renderTargetBright=new $(i,r,{type:N}),this.renderTargetBright.texture.name="UnrealBloomPass.bright",this.renderTargetBright.texture.generateMipmaps=!1;for(let u=0;u<this.nMips;u++){const w=new $(i,r,{type:N});w.texture.name="UnrealBloomPass.h"+u,w.texture.generateMipmaps=!1,this.renderTargetsHorizontal.push(w);const M=new $(i,r,{type:N});M.texture.name="UnrealBloomPass.v"+u,M.texture.generateMipmaps=!1,this.renderTargetsVertical.push(M),i=Math.round(i/2),r=Math.round(r/2)}const n=qe;this.highPassUniforms=U.clone(n.uniforms),this.highPassUniforms.luminosityThreshold.value=a,this.highPassUniforms.smoothWidth.value=.01,this.materialHighPassFilter=new x({uniforms:this.highPassUniforms,vertexShader:n.vertexShader,fragmentShader:n.fragmentShader}),this.separableBlurMaterials=[];const l=[3,5,7,9,11];i=Math.round(this.resolution.x/2),r=Math.round(this.resolution.y/2);for(let u=0;u<this.nMips;u++)this.separableBlurMaterials.push(this.getSeperableBlurMaterial(l[u])),this.separableBlurMaterials[u].uniforms.invSize.value=new f(1/i,1/r),i=Math.round(i/2),r=Math.round(r/2);this.compositeMaterial=this.getCompositeMaterial(this.nMips),this.compositeMaterial.uniforms.blurTexture1.value=this.renderTargetsVertical[0].texture,this.compositeMaterial.uniforms.blurTexture2.value=this.renderTargetsVertical[1].texture,this.compositeMaterial.uniforms.blurTexture3.value=this.renderTargetsVertical[2].texture,this.compositeMaterial.uniforms.blurTexture4.value=this.renderTargetsVertical[3].texture,this.compositeMaterial.uniforms.blurTexture5.value=this.renderTargetsVertical[4].texture,this.compositeMaterial.uniforms.bloomStrength.value=t,this.compositeMaterial.uniforms.bloomRadius.value=.1;const c=[1,.8,.6,.4,.2];this.compositeMaterial.uniforms.bloomFactors.value=c,this.bloomTintColors=[new C(1,1,1),new C(1,1,1),new C(1,1,1),new C(1,1,1),new C(1,1,1)],this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors;const g=le;this.copyUniforms=U.clone(g.uniforms),this.blendMaterial=new x({uniforms:this.copyUniforms,vertexShader:g.vertexShader,fragmentShader:g.fragmentShader,blending:ne,depthTest:!1,depthWrite:!1,transparent:!0}),this.enabled=!0,this.needsSwap=!1,this._oldClearColor=new z,this.oldClearAlpha=1,this.basic=new ye,this.fsQuad=new V(null)}dispose(){for(let e=0;e<this.renderTargetsHorizontal.length;e++)this.renderTargetsHorizontal[e].dispose();for(let e=0;e<this.renderTargetsVertical.length;e++)this.renderTargetsVertical[e].dispose();this.renderTargetBright.dispose();for(let e=0;e<this.separableBlurMaterials.length;e++)this.separableBlurMaterials[e].dispose();this.compositeMaterial.dispose(),this.blendMaterial.dispose(),this.basic.dispose(),this.fsQuad.dispose()}setSize(e,t){let s=Math.round(e/2),a=Math.round(t/2);this.renderTargetBright.setSize(s,a);for(let i=0;i<this.nMips;i++)this.renderTargetsHorizontal[i].setSize(s,a),this.renderTargetsVertical[i].setSize(s,a),this.separableBlurMaterials[i].uniforms.invSize.value=new f(1/s,1/a),s=Math.round(s/2),a=Math.round(a/2)}render(e,t,s,a,i){e.getClearColor(this._oldClearColor),this.oldClearAlpha=e.getClearAlpha();const r=e.autoClear;e.autoClear=!1,e.setClearColor(this.clearColor,0),i&&e.state.buffers.stencil.setTest(!1),this.renderToScreen&&(this.fsQuad.material=this.basic,this.basic.map=s.texture,e.setRenderTarget(null),e.clear(),this.fsQuad.render(e)),this.highPassUniforms.tDiffuse.value=s.texture,this.highPassUniforms.luminosityThreshold.value=this.threshold,this.fsQuad.material=this.materialHighPassFilter,e.setRenderTarget(this.renderTargetBright),e.clear(),this.fsQuad.render(e);let n=this.renderTargetBright;for(let l=0;l<this.nMips;l++)this.fsQuad.material=this.separableBlurMaterials[l],this.separableBlurMaterials[l].uniforms.colorTexture.value=n.texture,this.separableBlurMaterials[l].uniforms.direction.value=S.BlurDirectionX,e.setRenderTarget(this.renderTargetsHorizontal[l]),e.clear(),this.fsQuad.render(e),this.separableBlurMaterials[l].uniforms.colorTexture.value=this.renderTargetsHorizontal[l].texture,this.separableBlurMaterials[l].uniforms.direction.value=S.BlurDirectionY,e.setRenderTarget(this.renderTargetsVertical[l]),e.clear(),this.fsQuad.render(e),n=this.renderTargetsVertical[l];this.fsQuad.material=this.compositeMaterial,this.compositeMaterial.uniforms.bloomStrength.value=this.strength,this.compositeMaterial.uniforms.bloomRadius.value=this.radius,this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors,e.setRenderTarget(this.renderTargetsHorizontal[0]),e.clear(),this.fsQuad.render(e),this.fsQuad.material=this.blendMaterial,this.copyUniforms.tDiffuse.value=this.renderTargetsHorizontal[0].texture,i&&e.state.buffers.stencil.setTest(!0),this.renderToScreen?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(s),this.fsQuad.render(e)),e.setClearColor(this._oldClearColor,this.oldClearAlpha),e.autoClear=r}getSeperableBlurMaterial(e){const t=[];for(let s=0;s<e;s++)t.push(.39894*Math.exp(-.5*s*s/(e*e))/e);return new x({defines:{KERNEL_RADIUS:e},uniforms:{colorTexture:{value:null},invSize:{value:new f(.5,.5)},direction:{value:new f(.5,.5)},gaussianCoefficients:{value:t}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`#include <common>
				varying vec2 vUv;
				uniform sampler2D colorTexture;
				uniform vec2 invSize;
				uniform vec2 direction;
				uniform float gaussianCoefficients[KERNEL_RADIUS];

				void main() {
					float weightSum = gaussianCoefficients[0];
					vec3 diffuseSum = texture2D( colorTexture, vUv ).rgb * weightSum;
					for( int i = 1; i < KERNEL_RADIUS; i ++ ) {
						float x = float(i);
						float w = gaussianCoefficients[i];
						vec2 uvOffset = direction * invSize * x;
						vec3 sample1 = texture2D( colorTexture, vUv + uvOffset ).rgb;
						vec3 sample2 = texture2D( colorTexture, vUv - uvOffset ).rgb;
						diffuseSum += (sample1 + sample2) * w;
						weightSum += 2.0 * w;
					}
					gl_FragColor = vec4(diffuseSum/weightSum, 1.0);
				}`})}getCompositeMaterial(e){return new x({defines:{NUM_MIPS:e},uniforms:{blurTexture1:{value:null},blurTexture2:{value:null},blurTexture3:{value:null},blurTexture4:{value:null},blurTexture5:{value:null},bloomStrength:{value:1},bloomFactors:{value:null},bloomTintColors:{value:null},bloomRadius:{value:0}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`varying vec2 vUv;
				uniform sampler2D blurTexture1;
				uniform sampler2D blurTexture2;
				uniform sampler2D blurTexture3;
				uniform sampler2D blurTexture4;
				uniform sampler2D blurTexture5;
				uniform float bloomStrength;
				uniform float bloomRadius;
				uniform float bloomFactors[NUM_MIPS];
				uniform vec3 bloomTintColors[NUM_MIPS];

				float lerpBloomFactor(const in float factor) {
					float mirrorFactor = 1.2 - factor;
					return mix(factor, mirrorFactor, bloomRadius);
				}

				void main() {
					gl_FragColor = bloomStrength * ( lerpBloomFactor(bloomFactors[0]) * vec4(bloomTintColors[0], 1.0) * texture2D(blurTexture1, vUv) +
						lerpBloomFactor(bloomFactors[1]) * vec4(bloomTintColors[1], 1.0) * texture2D(blurTexture2, vUv) +
						lerpBloomFactor(bloomFactors[2]) * vec4(bloomTintColors[2], 1.0) * texture2D(blurTexture3, vUv) +
						lerpBloomFactor(bloomFactors[3]) * vec4(bloomTintColors[3], 1.0) * texture2D(blurTexture4, vUv) +
						lerpBloomFactor(bloomFactors[4]) * vec4(bloomTintColors[4], 1.0) * texture2D(blurTexture5, vUv) );
				}`})}}S.BlurDirectionX=new f(1,0);S.BlurDirectionY=new f(0,1);const Qe={name:"OutputShader",uniforms:{tDiffuse:{value:null},toneMappingExposure:{value:1}},vertexShader:`
		precision highp float;

		uniform mat4 modelViewMatrix;
		uniform mat4 projectionMatrix;

		attribute vec3 position;
		attribute vec2 uv;

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`
	
		precision highp float;

		uniform sampler2D tDiffuse;

		#include <tonemapping_pars_fragment>
		#include <colorspace_pars_fragment>

		varying vec2 vUv;

		void main() {

			gl_FragColor = texture2D( tDiffuse, vUv );

			// tone mapping

			#ifdef LINEAR_TONE_MAPPING

				gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );

			#elif defined( REINHARD_TONE_MAPPING )

				gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );

			#elif defined( CINEON_TONE_MAPPING )

				gl_FragColor.rgb = OptimizedCineonToneMapping( gl_FragColor.rgb );

			#elif defined( ACES_FILMIC_TONE_MAPPING )

				gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );

			#elif defined( AGX_TONE_MAPPING )

				gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );

			#endif

			// color space

			#ifdef SRGB_TRANSFER

				gl_FragColor = sRGBTransferOETF( gl_FragColor );

			#endif

		}`};class Ve extends T{constructor(){super();const e=Qe;this.uniforms=U.clone(e.uniforms),this.material=new xe({name:e.name,uniforms:this.uniforms,vertexShader:e.vertexShader,fragmentShader:e.fragmentShader}),this.fsQuad=new V(this.material),this._outputColorSpace=null,this._toneMapping=null}render(e,t,s){this.uniforms.tDiffuse.value=s.texture,this.uniforms.toneMappingExposure.value=e.toneMappingExposure,(this._outputColorSpace!==e.outputColorSpace||this._toneMapping!==e.toneMapping)&&(this._outputColorSpace=e.outputColorSpace,this._toneMapping=e.toneMapping,this.material.defines={},Ce.getTransfer(this._outputColorSpace)===Se&&(this.material.defines.SRGB_TRANSFER=""),this._toneMapping===Te?this.material.defines.LINEAR_TONE_MAPPING="":this._toneMapping===Me?this.material.defines.REINHARD_TONE_MAPPING="":this._toneMapping===Ee?this.material.defines.CINEON_TONE_MAPPING="":this._toneMapping===Ae?this.material.defines.ACES_FILMIC_TONE_MAPPING="":this._toneMapping===Re&&(this.material.defines.AGX_TONE_MAPPING=""),this.material.needsUpdate=!0),this.renderToScreen===!0?(e.setRenderTarget(null),this.fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this.fsQuad.render(e))}dispose(){this.material.dispose(),this.fsQuad.dispose()}}const q=["0","1","2","3","4","5","6","7","8","9","$",".","-","+",",","?","✓","·","→"],ce=["3,912.44","113.44","DR","CR","1310","6810","6410","1250","GL","AP","AR","JE","FX","EUR","P-0317","403","SHA-256"],j=[...q,...ce],_=8,de=Math.ceil(j.length/_),E=512,I=128,je=.62;function Je(o){return function(){o|=0,o=o+1831565813|0;const e=Math.imul(o^o>>>15,1|o),t=e+Math.imul(e^e>>>7,61|e)^e;return((t^t>>>14)>>>0)/4294967296}}const A=Je(20261025);function Ke(){const o=document.createElement("canvas");o.width=E*_,o.height=I*de;const e=o.getContext("2d");e.fillStyle="#000",e.fillRect(0,0,o.width,o.height),e.fillStyle="#fff",e.textAlign="center",e.textBaseline="middle",j.forEach((s,a)=>{const i=a%_,r=Math.floor(a/_);let n=I*je;e.font=`600 ${n}px Fira Mono, monospace`;const l=e.measureText(s).width;l>E*.94&&(n*=E*.94/l,e.font=`600 ${n}px Fira Mono, monospace`),e.fillText(s,i*E+E/2,r*I+I/2)});const t=new Fe(o);return t.generateMipmaps=!0,t.minFilter=$e,t.magFilter=Ne,t}function Xe(){const o=document.getElementById("particle-canvas");if(!o)return;const e=window.innerWidth<768,t=window.matchMedia("(prefers-reduced-motion: reduce)").matches,s=new _e,a=new Pe(38,window.innerWidth/window.innerHeight,.1,100);a.position.set(0,3.1,11.2),a.lookAt(0,.9,-2.2);const i=o.getContext("webgl2",{alpha:!0,antialias:!e,powerPreference:e?"low-power":"high-performance"});if(!i){console.error("WebGL2 not supported");return}const r=new Le({canvas:o,context:i,alpha:!0});r.setPixelRatio(Math.min(window.devicePixelRatio,e?1:2)),r.setSize(window.innerWidth,window.innerHeight),r.setClearColor(0,0);const n=new Ge(r);n.setPixelRatio(r.getPixelRatio()),n.setSize(window.innerWidth,window.innerHeight),n.addPass(new We(s,a));const l=new S(new f(window.innerWidth,window.innerHeight),e?.5:.95,.5,.22);n.addPass(l),n.addPass(new Ve);const c=e?48:64,g=e?64:96,u=.42,w=.22,M=5.2,P=c*g,fe=Ke(),L=new Float32Array(P*3),J=new Float32Array(P*4),K=new Float32Array(P*2);for(let d=0;d<g;d++)for(let v=0;v<c;v++){const h=d*c+v;L[h*3]=(v-(c-1)/2)*u,L[h*3+1]=0,L[h*3+2]=M-d*w,J.set([A(),A(),A(),A()],h*4);const pe=Math.floor(A()*j.length);K.set([pe,0],h*2)}const H=new Be(1,1),p=new Ie;p.index=H.index,p.setAttribute("position",H.attributes.position),p.setAttribute("uv",H.attributes.uv),p.setAttribute("aGrid",new k(L,3)),p.setAttribute("aSeed",new k(J,4)),p.setAttribute("aInfo",new k(K,2)),p.instanceCount=P,p.boundingSphere=new De(new C,60);const X=new x({transparent:!0,depthWrite:!1,blending:ne,uniforms:{uTime:{value:0},uBlob:{value:0},uScroll:{value:0},uAtlas:{value:fe},uCols:{value:_},uRows:{value:de}},vertexShader:`
      uniform float uTime, uBlob, uScroll;
      uniform float uCols, uRows;
      in vec3 aGrid;
      in vec4 aSeed;
      in vec2 aInfo;
      out vec2 vUv;
      out vec3 vColor;
      out float vAlpha;
      
      float hash(float n) { return fract(sin(n) * 43758.5453123); }
      
      vec3 hsv2rgb(vec3 c) {
        vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
      }
      
      void main() {
        float t = uTime;
        vec3 g = aGrid;
        vec2 blobC = vec2(0.0, -2.6);
        vec2 d2 = g.xz - blobC;
        float d = length(d2);
        
        float h = sin(g.x * 0.16 + t * 0.34) * cos(g.z * 0.17 + t * 0.34) * 2.3;
        float R = 3.9;
        float b = exp(-d * d / (R * R));
        float dome = uBlob * b * (2.7 + sin(t + d) * 0.5);
        
        vec3 p = g + vec3(0.0, h + dome, 0.0) * (1.0 - uScroll * 0.8);
        
        vec3 camR = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 camU = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        
        float s = 0.16 * (0.7 + 0.65 * aSeed.w) * (1.0 + 0.12 * b * uBlob);
        vec3 world = p + position.x * 4.0 * s * camR + position.y * s * camU;
        
        float rate = 2.5 + aSeed.y * 8.0;
        float tick = floor(t * rate + aSeed.z * 17.0);
        float r1 = hash(aSeed.x * 91.7 + tick * 1.37);
        float glyphIdx = r1 < 0.7 ? floor(r1 / 0.7 * ${q.length}.0) : ${q.length}.0 + floor((r1 - 0.7) / 0.3 * ${ce.length}.0);
        
        float colI = mod(glyphIdx, uCols);
        float rowI = floor(glyphIdx / uCols);
        vUv = vec2((colI + uv.x) / uCols, 1.0 - (rowI + 1.0 - uv.y) / uRows);
        
        float hn = clamp((h + dome * 0.7 + 0.5) / 2.4, 0.0, 1.0);
        float hue = mix(0.03, 0.09, hn);
        float sat = mix(0.8, 0.9, hn);
        float val = mix(0.4, 1.0, hn * hn);
        vColor = hsv2rgb(vec3(hue, sat, val));
        
        vec4 mv = viewMatrix * vec4(world, 1.0);
        float depth = -mv.z;
        float fog = (1.0 - smoothstep(13.0, 30.0, depth)) * smoothstep(0.8, 2.5, depth);
        vAlpha = fog * (1.0 - uScroll * 0.5);
        
        gl_Position = projectionMatrix * mv;
      }
    `,fragmentShader:`
      precision highp float;
      uniform sampler2D uAtlas;
      in vec2 vUv;
      in vec3 vColor;
      in float vAlpha;
      layout(location = 0) out vec4 fragColor;
      
      void main() {
        float a = texture(uAtlas, vUv).r;
        a = smoothstep(0.02, 0.9, a);
        if (a * vAlpha < 0.002) discard;
        fragColor = vec4(vColor * a * vAlpha, 1.0);
      }
    `}),Y=new oe(p,X);Y.frustumCulled=!1,s.add(Y);const Z=document.getElementById("hero-labels");Z&&!t&&[{text:"PAYPAL *INST XFER −$3,912.44",x:50,y:12},{text:"1310 · $3,451.50 · EUR crew deposit",x:75,y:28},{text:"6810 · $147.50 · wire fees",x:25,y:72,brightness:1.3},{text:"6410 · $200.00 · Claude API",x:80,y:85},{text:"1250 · $113.44 · Steam · reimburse",x:15,y:88}].forEach((d,v)=>{const h=document.createElement("div");h.className="hero-label",h.textContent=d.text,h.style.left=`${d.x}%`,h.style.top=`${d.y}%`,h.style.animationDelay=`${v*.8}s`,d.brightness&&(h.style.filter=`brightness(${d.brightness})`),Z.appendChild(h)});let ee=0,O=0,me=!t;function te(){requestAnimationFrame(te),me&&(ee+=t?0:.016);const d=X.uniforms;d.uTime.value=ee,d.uBlob.value=1-O*.6,d.uScroll.value=O,n.render()}te(),window.addEventListener("scroll",()=>{const d=document.getElementById("hero");if(d){const v=d.getBoundingClientRect();O=Math.max(0,Math.min(1,1-v.bottom/window.innerHeight))}}),window.addEventListener("resize",()=>{a.aspect=window.innerWidth/window.innerHeight,a.updateProjectionMatrix(),r.setSize(window.innerWidth,window.innerHeight),n.setSize(window.innerWidth,window.innerHeight)})}let b="new";const m=[];let Ye=0;const ue="0000000000000000000000000000000000000000000000000000000000000000";async function he(o,e){const t=o+e,s=new TextEncoder().encode(t),a=await crypto.subtle.digest("SHA-256",s);return Array.from(new Uint8Array(a)).map(r=>r.toString(16).padStart(2,"0")).join("")}async function y(o,e,t){const s=new Date().toISOString(),a=m.length>0?m[m.length-1].hash:ue,i=`${s}|${o}|${e}|${t}`,r=await he(a,i);m.push({id:++Ye,timestamp:s,action:o,actor:e,data:t,prevHash:a,hash:r}),Q()}function Q(){const o=document.getElementById("audit-log");o&&(o.innerHTML=m.map(e=>`
    <div class="audit-entry ${e.tampered?"tampered":""}" data-id="${e.id}">
      <div><strong>#${e.id}</strong> ${e.action} by ${e.actor}</div>
      <div>${e.data}</div>
      <div class="audit-entry-hash">prev: ${e.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${e.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function D(){const o=document.getElementById("state-display");o&&(o.textContent=b);const e=document.getElementById("btn-ask"),t=document.getElementById("btn-approve-ctrl"),s=document.getElementById("btn-approve-jarvis");e&&(e.disabled=b!=="proposed"&&b!=="needs_info"),t&&(t.disabled=b!=="proposed"),s&&(s.disabled=b!=="proposed")}function F(o,e=!1){const t=document.getElementById("state-message");t&&(t.textContent=o,t.className=e?"state-message error":"state-message")}function Ze(){y("INIT","SYSTEM","Work item created");const o=document.getElementById("btn-propose"),e=document.getElementById("btn-ask"),t=document.getElementById("btn-approve-ctrl"),s=document.getElementById("btn-approve-jarvis"),a=document.getElementById("btn-tamper"),i=document.getElementById("btn-verify");o==null||o.addEventListener("click",async()=>{b="proposed",await y("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),D(),F("Entry proposed. Awaiting Controller approval.")}),e==null||e.addEventListener("click",async()=>{b="needs_info",await y("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),D(),F("Asked Controller for clarification.")}),t==null||t.addEventListener("click",async()=>{b="approved",await y("APPROVE","Controller","Approved for posting"),D(),F("Approved by Controller. Ready to post.")}),s==null||s.addEventListener("click",async()=>{await y("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await y("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),F("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),a==null||a.addEventListener("click",()=>{m.length>=2&&(m[1].data="TAMPERED DATA - expense all to Software",m[1].tampered=!0,Q(),G("",!1))}),i==null||i.addEventListener("click",async()=>{let r=!0,n=-1;for(let l=0;l<m.length;l++){const c=m[l],g=l===0?ue:m[l-1].hash;if(c.prevHash!==g){r=!1,n===-1&&(n=l);break}const u=`${c.timestamp}|${c.action}|${c.actor}|${c.data}`,w=await he(c.prevHash,u);c.hash!==w?(r=!1,n===-1&&(n=l),c.tampered=!0):c.tampered=!1}Q(),r?G("✓ Audit log verified. Hash chain intact.",!0):G(`❌ Chain broken at entry #${n+1}. Tampering detected.`,!1)}),et(),tt(),D()}function G(o,e){const t=document.getElementById("verify-result");t&&(t.textContent=o,t.className=e?"verify-result valid":"verify-result invalid")}function et(){const o=document.querySelectorAll(".btn-challenge"),e=document.getElementById("custom-challenge"),t=document.getElementById("btn-custom-challenge"),s=document.getElementById("challenge-response"),a=document.getElementById("btn-new-evidence"),i={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};o.forEach(r=>{r.addEventListener("click",()=>{const n=r.getAttribute("data-challenge");n&&s&&(s.innerHTML=`
          <div><strong>Challenge:</strong> ${r.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${i[n]}</div>
        `)})}),t==null||t.addEventListener("click",()=>{const r=e==null?void 0:e.value.trim();if(r&&s){let n="I understand your concern. Let me look up the relevant policy and precedent...";r.toLowerCase().includes("material")?n=i.materiality:r.toLowerCase().includes("simple")||r.toLowerCase().includes("complex")?n=i.simpler:(r.toLowerCase().includes("next")||r.toLowerCase().includes("later"))&&(n=i.timing),s.innerHTML=`
        <div><strong>Challenge:</strong> ${r}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${n}</div>
      `}}),a==null||a.addEventListener("click",async()=>{s&&(s.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await y("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function tt(){const o=document.querySelectorAll(".btn-scenario"),e=document.getElementById("scenario-output"),t={"vendor-scam":`
      <div><strong>Scenario:</strong> Vendor email requests bank change</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ⚠️ Payment FROZEN<br>
        State: NEEDS_INFO<br>
        Reason: Bank detail change detected. Calling number on file (not email) to verify.<br>
        Evidence: Email headers logged, payment on hold pending voice confirmation.
      </div>
    `,"split-purchase":`
      <div><strong>Scenario:</strong> Multiple $2,400 purchases (under $2,500 limit)</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        🚨 ESCALATED to Controller<br>
        Reason: Pattern matches split-purchase evasion. Same vendor, similar amounts, consecutive days.<br>
        Aggregate total: $9,600 (exceeds approval threshold)<br>
        Awaiting guidance before posting.
      </div>
    `,"refund-revenue":`
      <div><strong>Scenario:</strong> Refund coded as revenue</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ✏️ RECLASS proposed<br>
        Original: DR Cash / CR Revenue $1,500<br>
        Corrected: DR Cash / CR Expense (reversal) $1,500<br>
        Reason: Credit to a revenue account overstates income. Refunds reduce the original expense, not create revenue.
      </div>
    `};o.forEach(s=>{s.addEventListener("click",()=>{const a=s.getAttribute("data-scenario");a&&e&&(e.innerHTML=t[a]||"")})})}const it=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function st(){const o=document.getElementById("glossary-grid"),e=document.getElementById("glossary-search");function t(s=""){if(!o)return;const a=it.filter(({term:i,definition:r})=>i.toLowerCase().includes(s.toLowerCase())||r.toLowerCase().includes(s.toLowerCase()));o.innerHTML=a.map(({term:i,definition:r})=>`
      <div class="glossary-term">
        <h4>${i}</h4>
        <p>${r}</p>
      </div>
    `).join("")}t(),e==null||e.addEventListener("input",s=>{t(s.target.value)})}const W=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function R(o){return"$"+o.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function at(){const o=document.getElementById("bank-line"),e=document.getElementById("split-cards"),t=document.getElementById("balance-table");let s=!1;o==null||o.addEventListener("click",()=>{s||(s=!0,B.to(o,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{a()}}))});function a(){if(!e||!t)return;e.innerHTML=W.map(n=>`
      <div class="split-card">
        <div class="split-account">${n.account}</div>
        <div class="split-name">${n.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${n.detail}</div>
        <div class="split-amount">${R(n.amount)}</div>
      </div>
    `).join(""),B.to(e,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{i()}}),e.querySelectorAll(".split-card").forEach((n,l)=>{B.from(n,{duration:.6,delay:l*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function i(){if(!t)return;const r=W.reduce((n,l)=>n+l.amount,0);t.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${W.map(n=>`
            <tr>
              <td>${n.account} ${n.name}</td>
              <td>${R(n.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${R(r)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${R(r)}</td>
            <td>${R(r)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,B.to(t,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function ae(){const o=document.createElement("canvas");if(o.getContext("webgl")||o.getContext("experimental-webgl"))try{Xe()}catch(t){console.warn("WebGL initialization failed, using fallback",t),re()}else re();at(),Ze(),st(),rt()}function rt(){const o=document.querySelectorAll(".tab-button");o.forEach(r=>{r.addEventListener("click",()=>{const n=r.getAttribute("data-tab");o.forEach(c=>c.classList.remove("active")),r.classList.add("active"),document.querySelectorAll(".tab-content").forEach(c=>{c.classList.remove("active")});const l=document.querySelector(`[data-tab-content="${n}"]`);l&&l.classList.add("active")})});const e=document.querySelectorAll(".faq-item");e.forEach(r=>{const n=r.querySelector(".faq-question");n==null||n.addEventListener("click",()=>{const l=r.classList.contains("active");e.forEach(c=>c.classList.remove("active")),l||r.classList.add("active")})});const t=document.querySelectorAll(".glass-layer"),s=document.querySelectorAll(".trust-detail");t.forEach((r,n)=>{r.addEventListener("click",()=>{t.forEach(c=>c.classList.remove("active")),r.classList.add("active"),s.forEach(c=>c.classList.remove("active"));const l=document.querySelector(`[data-detail="${n+1}"]`);l&&l.classList.add("active")})}),t.length>0&&s.length>0&&(t[0].classList.add("active"),s[0].classList.add("active"));const a=document.querySelector(".mobile-menu-toggle"),i=document.querySelector(".nav-links");a==null||a.addEventListener("click",()=>{i==null||i.classList.toggle("active")}),document.querySelectorAll('a[href^="#"]').forEach(r=>{r.addEventListener("click",n=>{n.preventDefault();const l=document.querySelector(r.getAttribute("href")||"");l&&l.scrollIntoView({behavior:"smooth",block:"start"})})})}function re(){const o=document.getElementById("particle-canvas");if(o){o.style.display="none";const t=document.getElementById("hero");t&&(t.style.background="linear-gradient(135deg, #6b1d2a 0%, #0a0a0a 50%, #ff7a1a 100%)")}const e=document.getElementById("arch-canvas");if(e){const t=e.getContext("2d");t&&(e.width=e.clientWidth,e.height=e.clientHeight,t.fillStyle="#141414",t.fillRect(0,0,e.width,e.height),t.fillStyle="#ff7a1a",t.font="16px Fira Mono",t.textAlign="center",t.fillText("WebGL unavailable - 3D visualization disabled",e.width/2,e.height/2))}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",ae):ae();
